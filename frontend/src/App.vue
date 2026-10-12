<script setup>
import {ref,onMounted,onUnmounted,computed} from 'vue'
const jobs=ref([]), selected=ref(null), timeline=ref([]), busy=ref(false), error=ref(''), fileInput=ref(null)
const jobError=ref(''), showError=ref(false)
const cfg=ref({})
function normalizeErrorText(raw){
  const text = String(raw || '').trim()
  if(!text) return '暂无详细错误信息'
  const withoutTrace = text.replace(/^Traceback \(most recent call last\):\n?/i, '')
  const lines = withoutTrace.split(/\n/).map(x => x.trim()).filter(Boolean)
  const lastNonFrame = [...lines].reverse().find(line => !line.startsWith('File "') && !line.startsWith('File ') && !line.startsWith('  '))
  return lastNonFrame || lines[lines.length - 1] || text
}
const activeErrorSummary = computed(() => normalizeErrorText(jobError.value))
async function api(url,opt={}){const r=await fetch(url,opt); if(!r.ok) throw new Error(await r.text()); return r.json()}
async function refresh(){jobs.value=await api('/api/jobs'); if(selected.value){const x=jobs.value.find(j=>j.id===selected.value.id); if(x) selected.value=x}}
async function select(j){
  selected.value=j
  timeline.value=await api(`/api/jobs/${j.id}/timeline`)
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
const active=computed(()=>selected.value)
let timer
onMounted(async()=>{cfg.value=await api('/api/config'); await refresh(); timer=setInterval(refresh,2000)})
onUnmounted(()=>clearInterval(timer))
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
<div class="top"><div><h2>{{active.filename}}</h2><p>{{active.status}} · {{fmt(active.duration)}}</p></div><div class="actions"><button v-if="active.status==='failed'" @click="retry(active)">继续重试</button><button v-if="active.status==='failed'" @click="fetchError(active)">查看错误日志</button><button v-if="active.status==='running'" class="danger" @click="cancel(active)">取消</button><a v-if="active.status==='done'" :href="`/api/jobs/${active.id}/files/${encodeURIComponent(active.filename.replace(/\.[^.]+$/,'')+'.md')}`" target="_blank">打开 Markdown</a></div></div>
<audio v-if="active" controls :src="`/api/jobs/${active.id}/audio`"></audio>
<div class="stats"><div><b>{{timeline.length}}</b><span>segments</span></div><div><b>{{cfg.diarization_provider}}</b><span>speaker</span></div><div><b>{{cfg.llm_enabled?'云端':'本地'}}</b><span>translation</span></div></div>
<div class="transcript"><div v-for="(s,i) in timeline" :key="i" class="line"><div class="time">{{fmt(s.start)}} — {{fmt(s.end)}}</div><div class="speaker">{{s.speaker||'SPEAKER_00'}}</div><div class="text">{{s.text}}<div v-if="s.translated" class="zh">{{s.translated}}</div></div></div><div v-if="!timeline.length" class="empty">任务完成后，这里显示带时间轴的 transcript。</div></div>
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
