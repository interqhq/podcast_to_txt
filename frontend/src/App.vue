<script setup>
import {ref,onMounted,onUnmounted,computed,nextTick,watch} from 'vue'
const jobs=ref([]), selected=ref(null), timeline=ref([]), busy=ref(false), error=ref(''), fileInput=ref(null)
const jobError=ref(''), showError=ref(false)
const cfg=ref({})
const audioRef=ref(null)
const transcriptRef=ref(null)
const currentTime=ref(0)
const refreshing=ref(false)
const lastTimelineUpdatedAt=ref('')
const exporting=ref(false)
const exportMessage=ref('')

function normalizeErrorText(raw){
  const text = String(raw || '').trim()
  if(!text) return '暂无详细错误信息'
  const withoutTrace = text.replace(/^Traceback \(most recent call last\):\n?/i, '')
  const lines = withoutTrace.split(/\n/).map(x => x.trim()).filter(Boolean)
  const lastNonFrame = [...lines].reverse().find(line => !line.startsWith('File "') && !line.startsWith('File ') && !line.startsWith('  '))
  return lastNonFrame || lines[lines.length - 1] || text
}
const activeErrorSummary = computed(() => normalizeErrorText(jobError.value))
const currentSegmentIndex = computed(() => {
  const list = timeline.value || []
  if (!list.length) return -1
  let candidate = -1
  for (let i = 0; i < list.length; i++) {
    const seg = list[i]
    const start = Number(seg.start || 0)
    const end = Number(seg.end ?? start + 1)
    if (currentTime.value < start) break
    if (currentTime.value >= start && currentTime.value <= end) {
      candidate = i
      break
    }
  }
  if (candidate === -1) {
    for (let i = list.length - 1; i >= 0; i--) {
      if (Number(list[i].start || 0) <= currentTime.value) {
        candidate = i
        break
      }
    }
  }
  return candidate
})
const currentSegment = computed(() => {
  const idx = currentSegmentIndex.value
  return idx >= 0 ? timeline.value[idx] : null
})

async function api(url,opt={}){const r=await fetch(url,opt); if(!r.ok) throw new Error(await r.text()); return r.json()}
function formatErr(e){ return e instanceof Error ? e.message : String(e) }
async function refresh(){
  if(refreshing.value) return
  refreshing.value=true
  try{
    jobs.value=await api('/api/jobs')
    if(selected.value){
      const prev = selected.value
      const x=jobs.value.find(j=>j.id===selected.value.id)
      if(!x){
        selected.value=null
        timeline.value=[]
        lastTimelineUpdatedAt.value=''
        return
      }
      selected.value=x
      const shouldReloadTimeline =
        !timeline.value.length ||
        x.status==='running' ||
        x.status==='queued' ||
        x.updated_at!==lastTimelineUpdatedAt.value ||
        x.updated_at!==prev.updated_at
      if(shouldReloadTimeline){
        timeline.value=await api(`/api/jobs/${x.id}/timeline`)
        lastTimelineUpdatedAt.value=x.updated_at || ''
        nextTick(ensureCurrentSegmentVisible)
      }
      if(x.status==='failed' && !jobError.value){
        await fetchError(x)
      }
    }
  } finally {
    refreshing.value=false
  }
}
async function select(j){
  selected.value=j
  timeline.value=await api(`/api/jobs/${j.id}/timeline`)
  lastTimelineUpdatedAt.value=j.updated_at || ''
  currentTime.value = 0
  nextTick(ensureCurrentSegmentVisible)
  if(j.status==='failed') {
    await fetchError(j)
  } else {
    jobError.value=''; showError.value=false
  }
}
async function upload(files){for(const file of files){const fd=new FormData();fd.append('file',file); await api('/api/jobs',{method:'POST',body:fd})} await refresh()}
function choose(e){upload([...e.target.files])}
function drop(e){upload([...e.dataTransfer.files].filter(f=>f.type.startsWith('audio/')||/\.(mp3|m4a|wav|flac|aac|ogg|opus|mp4|webm)$/i.test(f.name)))}
async function retry(j){await api(`/api/jobs/${j.id}/retry`,{method:'POST'}); await refresh()}
async function cancel(j){await api(`/api/jobs/${j.id}/cancel`,{method:'POST'}); await refresh()}
async function downloadJsonToLocal(j){
  exportMessage.value=''
  exporting.value=true
  try{
    const fileName = `${j.filename.replace(/\.[^.]+$/, '')}.json`
    const response = await fetch(`/api/jobs/${j.id}/files/${encodeURIComponent(fileName)}`)
    if(!response.ok) throw new Error(await response.text())
    const blob = await response.blob()
    if (window.showSaveFilePicker) {
      const handle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [{ description: 'JSON 文件', accept: { 'application/json': ['.json'] } }],
      })
      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()
      exportMessage.value = `已保存到本机选择位置：${fileName}`
      return
    }
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    exportMessage.value = `已下载到浏览器默认保存目录：${fileName}`
  }catch(e){
    exportMessage.value = `下载失败：${normalizeErrorText(formatErr(e))}`
  }finally{
    exporting.value=false
  }
}
async function remove(j){
	if(!confirm('确定删除该任务及其文件吗？')) return
	await api(`/api/jobs/${j.id}`,{method:'DELETE'})
	if(selected.value && selected.value.id===j.id) selected.value=null
	await refresh()
}
async function fetchError(j){
	try{
		const r = await api(`/api/jobs/${j.id}/error`)
		jobError.value = r.error || ''
	}catch(e){ jobError.value = String(e) }
	showError.value = true
}
function seekToSegment(seg){
  if(!seg || !audioRef.value) return
  audioRef.value.currentTime = Number(seg.start || 0)
  currentTime.value = Number(seg.start || 0)
  nextTick(ensureCurrentSegmentVisible)
}
function ensureCurrentSegmentVisible(){
  if(!transcriptRef.value) return
  const idx = currentSegmentIndex.value
  if(idx < 0) return
  const node = transcriptRef.value.querySelector(`[data-segment-index="${idx}"]`)
  if(!node) return
  const panelRect = transcriptRef.value.getBoundingClientRect()
  const rect = node.getBoundingClientRect()
  const withinView = rect.top >= panelRect.top && rect.bottom <= panelRect.bottom
  if(!withinView) node.scrollIntoView({behavior:'smooth', block:'nearest'})
}
function onTimeUpdate(e){
  currentTime.value = Number(e.target.currentTime || 0)
  ensureCurrentSegmentVisible()
}
const active=computed(()=>selected.value)
let timer
onMounted(async()=>{cfg.value=await api('/api/config'); await refresh(); timer=setInterval(refresh,2000)})
onUnmounted(()=>clearInterval(timer))
watch(() => timeline.value, () => { nextTick(ensureCurrentSegmentVisible) }, {flush:'post'})
function pct(j){return Math.round(j.progress||0)}
function fmt(sec){if(sec==null)return '--:--';sec=Math.max(0,Math.floor(sec));return `${String(Math.floor(sec/3600)).padStart(2,'0')}:${String(Math.floor(sec%3600/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')}`}
</script>
<template>
<div class="app">
<header><div><h1>Podcast Studio</h1><p>本地长音频转录 · Speaker · 翻译 · 剧本</p></div><div class="badge">{{cfg.asr_provider}} / {{cfg.asr_model}}</div></header>
<section class="drop" @dragover.prevent @drop.prevent="drop" @click="fileInput.click()"><input ref="fileInput" type="file" multiple hidden accept="audio/*,.mp3,.m4a,.wav,.flac,.aac,.ogg,.opus" @change="choose"><b>拖入 Podcast 音频</b><span>支持 MP3 / M4A / WAV / FLAC · 可批量</span></section>
<div class="layout">
<aside><div class="aside-title">任务 <small>{{jobs.length}}</small></div><div v-for="j in jobs" :key="j.id" class="job" :class="{sel:selected?.id===j.id}" @click="select(j)"><div class="job-name">{{j.filename}}</div><div class="meta"><span>{{j.step}}</span><span>{{pct(j)}}%</span></div><div class="bar"><i :style="{width:pct(j)+'%'}"></i></div><button class="delete" @click.stop="remove(j)">删除</button></div></aside>
<main v-if="active">
<div class="top"><div><h2>{{active.filename}}</h2><p>{{active.status}} · {{fmt(active.duration)}}</p></div><div class="actions"><button @click="refresh" :disabled="refreshing">{{ refreshing ? '刷新中…' : '刷新' }}</button><button v-if="active.status==='failed'" @click="retry(active)">继续重试</button><button v-if="active.status==='failed'" @click="fetchError(active)">查看错误日志</button><button v-if="active.status==='running'" class="danger" @click="cancel(active)">取消</button><button v-if="active.status==='done'" @click="downloadJsonToLocal(active)" :disabled="exporting">{{ exporting ? '下载中…' : '下载 JSON 到本机' }}</button><a v-if="active.status==='done'" :href="`/api/jobs/${active.id}/files/${encodeURIComponent(active.filename.replace(/\.[^.]+$/,'')+'.md')}`" target="_blank">打开 Markdown</a></div></div>
<div v-if="active.status==='done'" class="export-hint">
  <div>浏览器会弹出“保存文件”对话框，选择本机任意目录即可。</div>
  <div v-if="exportMessage">{{ exportMessage }}</div>
</div>
<audio v-if="active" ref="audioRef" controls :src="`/api/jobs/${active.id}/audio`" @timeupdate="onTimeUpdate"></audio>
<div class="stats"><div><b>{{timeline.length}}</b><span>segments</span></div><div><b>{{cfg.diarization_provider}}</b><span>speaker</span></div><div><b>{{cfg.llm_enabled?'云端':'本地'}}</b><span>translation</span></div></div>
<div v-if="timeline.length" class="playback-panel">
  <div class="playback-time">{{fmt(currentTime)}} / {{fmt(currentSegment?.end || active.duration)}}</div>
  <div class="playback-cue">
    <span class="cue-speaker">{{ currentSegment?.speaker || 'SPEAKER_00' }}</span>
    <span class="cue-text">{{ currentSegment?.text || '等待播放…' }}</span>
  </div>
</div>
<div class="transcript" ref="transcriptRef"><div v-for="(s,i) in timeline" :key="`seg-${i}`" :data-segment-index="i" class="line" :class="{active: currentSegmentIndex===i}" @click="seekToSegment(s)"><div class="time">{{fmt(s.start)}} — {{fmt(s.end)}}</div><div class="speaker">{{s.speaker||'SPEAKER_00'}}</div><div class="text">{{s.text}}<div v-if="s.translated" class="zh">{{s.translated}}</div></div></div><div v-if="!timeline.length" class="empty">任务完成后，这里显示带时间轴的 transcript。</div></div>
<div v-if="active && active.status==='failed'" style="margin:16px 20px 0;border:1px solid #f2c7c7;background:#fff7f7;border-radius:12px;padding:16px;color:#7a1e1e;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
    <div>
      <div style="font-weight:700;font-size:14px;margin-bottom:6px;">任务失败详情</div>
      <div style="font-size:12px;line-height:1.6;color:#9d4a4a;">{{ activeErrorSummary }}</div>
    </div>
    <button @click="showError=!showError" style="border:1px solid #e4b0b0;background:#fff;padding:7px 10px;border-radius:8px;color:#7a1e1e;cursor:pointer;white-space:nowrap;">{{ showError ? '隐藏日志' : '查看完整日志' }}</button>
  </div>
  <pre v-if="showError" style="margin-top:12px;padding:12px;border-radius:8px;background:#fff;border:1px solid #f0d4d4;white-space:pre-wrap;word-break:break-word;font-size:12px;line-height:1.5;color:#582222;">{{ jobError || '暂无错误内容' }}</pre>
</div>
</main><main v-else class="welcome"><h2>把 Podcast 拖进来</h2><p>原始音频保存在本机。ASR / Speaker 可以完全本地运行，云端只在启用 LLM 时接收文本。</p></main>
</div></div>
</template>
