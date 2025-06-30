<template>
  <div class="anydownload-header-row">
    <img src="/logo.png" alt="logo" class="anydownload-logo" />
    <div class="anydownload-title-gradient">AnyDownload</div>
  </div>
  <n-card title="抖音视频下载" class="douyin-downloader">
    <n-alert v-if="cookieStatus === 'none'" type="warning" class="cookie-alert" style="margin-bottom: 18px;">
      当前未检测到有效的抖音Cookie，请先配置Cookie，否则无法正常下载！
    </n-alert>
    <n-alert v-else-if="cookieStatus === 'invalid'" type="error" class="cookie-alert" style="margin-bottom: 18px;">
      检测到Cookie无效，请重新配置Cookie！
    </n-alert>
    <n-radio-group v-model:value="mode" name="mode" class="mode-group">
      <n-radio value="one">单视频下载</n-radio>
      <n-radio value="user">主页作品下载</n-radio>
    </n-radio-group>
    <n-input
      v-model:value="url"
      :placeholder="mode === 'one' ? '请输入抖音视频链接' : '请输入抖音用户主页链接'"
      class="input-url styled-input"
      clearable
    />
    <div class="button-group" style="display: flex; gap: 12px; margin-bottom: 12px; justify-content: center;">
      <n-button :loading="mode === 'one' ? loadingDownloadOne : loadingDownloadUser" type="primary" @click="handleDownload" class="download-btn">
        <template #icon>
          <n-icon><DownloadOutline /></n-icon>
        </template>
        {{ mode === 'one' ? '下载视频' : '下载主页作品' }}
      </n-button>
      <n-button
        v-if="mode === 'one'"
        :loading="loadingParse"
        @click="handleParseDirect"
        class="download-btn"
      >
        <template #icon>
          <n-icon><LinkOutline /></n-icon>
        </template>
        解析直链下载
      </n-button>
      <n-button
        v-else
        :loading="loadingParseUser"
        @click="handleParseUserDirect"
        class="download-btn"
      >
        <template #icon>
          <n-icon><LinkOutline /></n-icon>
        </template>
        批量直链解析
      </n-button>
    </div>
    <n-divider />
    <!-- 单视频下载提示区 -->
    <template v-if="mode === 'one'">
      <n-alert v-if="errorDownloadOne" type="error" :bordered="false" class="result-alert">
        {{ errorDownloadOne }}
      </n-alert>
      <n-alert v-if="progressOne" type="info" :bordered="false" class="result-alert">
        <div v-for="(line, idx) in progressOne.split('\n')" :key="idx" class="progress-line">{{ line }}</div>
      </n-alert>
      <n-alert v-if="resultOne && !errorDownloadOne" type="success" :bordered="false" class="result-alert">
        {{ resultOne.msg }}
      </n-alert>
      <n-alert v-if="directUrlOne" type="success" :bordered="false" class="result-alert">
        <a :href="getProxyUrl(directUrlOne)" :download="getFileNameFromUrl(directUrlOne)" @click.prevent="forceDownload(getProxyUrl(directUrlOne))">点击下载视频</a>
      </n-alert>
      <n-alert v-if="errorParseOne" type="error" :bordered="false" class="result-alert">
        {{ errorParseOne }}
      </n-alert>
    </template>
    <!-- 主页作品下载提示区 -->
    <template v-else>
      <n-alert v-if="errorDownloadUser" type="error" :bordered="false" class="result-alert">
        {{ errorDownloadUser }}
      </n-alert>
      <n-alert v-if="progressUser" type="info" :bordered="false" class="result-alert">
        <div v-for="(line, idx) in progressUser.split('\n')" :key="idx" class="progress-line">{{ line }}</div>
      </n-alert>
      <n-alert v-if="resultUser && !errorDownloadUser" type="success" :bordered="false" class="result-alert">
        {{ resultUser.msg }}
      </n-alert>
      <!-- 主页批量直链解析提示 -->
      <n-alert v-if="infoParseUser" type="info" :bordered="false" class="result-alert">
        {{ infoParseUser }}
      </n-alert>
      <n-alert v-if="errorParseUser" type="error" :bordered="false" class="result-alert">
        {{ errorParseUser }}
      </n-alert>
      <n-data-table
        v-if="parseUserList.length"
        :columns="columns"
        :data="parseUserList"
        :bordered="false"
        size="small"
        class="mt-2"
      />
    </template>
    <div class="cookie-btn-row">
      <template v-if="cookieStatus === 'ok' && !showCookieInput">
        <n-button type="info" @click="showCookieInput = true">重新设置Cookie</n-button>
      </template>
      <template v-else>
        <div class="cookie-input-row">
          <div style="display:flex;flex-direction:column;align-items:flex-start;width:420px;max-width:100%;">
            <n-input
              v-model:value="cookieInput"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 6 }"
              class="cookie-input-center"
              :input-props="{ style: 'text-align:center;' }"
              placeholder=""
            />
            <div class="cookie-tip-text">请粘贴你的抖音cookie字符串</div>
          </div>
          <div class="cookie-btns">
            <n-button type="primary" :loading="savingCookie" @click="saveCookie">保存</n-button>
            <n-button @click="cancelCookieInput" v-if="cookieStatus === 'ok'">取消</n-button>
          </div>
        </div>
      </template>
    </div>
  </n-card>
  <div class="cookie-manual">
    <div class="manual-title" @click="manualCollapsed = !manualCollapsed" style="cursor:pointer;user-select:none;display:flex;align-items:center;">
      <span style="flex:1;">如何获取抖音Cookie（详细操作步骤）</span>
      <span style="font-size:18px;color:#4dd0e1;transition:transform 0.2s;" :style="{transform: manualCollapsed ? 'rotate(0deg)' : 'rotate(90deg)'}">▶</span>
    </div>
    <n-collapse-transition :show="!manualCollapsed">
      <div v-if="!manualCollapsed">
        <ol class="manual-list">
          <li>在电脑浏览器（推荐 Chrome/Edge）访问 <b>https://www.douyin.com/</b> 并登录你的抖音账号。</li>
          <li>按 <b>F12</b> 打开开发者工具，切换到 <b>"应用"/"Application"</b> 选项卡。</li>
          <li>在左侧找到 <b>"存储"/"Storage"</b> → <b>"Cookies"</b> → <b>"https://www.douyin.com"</b>。</li>
          <li>在右侧 Cookie 列表中，<b>全选所有内容</b>（可点第一个再按 Shift+最后一个），右键选择 <b>"复制"/"Copy"</b>。</li>
          <li>回到本页面，点击"配置Cookie"按钮，在弹窗中<b>粘贴</b>刚才复制的 Cookie 内容，点击"保存"。</li>
          <li>保存成功后即可正常下载抖音视频，如遇风控请重新获取 Cookie。</li>
        </ol>
        <div class="manual-tip">提示：Cookie 是你的登录凭证，请勿泄露给他人，仅用于本工具配置。</div>
      </div>
    </n-collapse-transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, h, onMounted } from 'vue'
import { useMessage, NCard, NInput, NButton, NRadioGroup, NRadio, NDivider, NAlert, NIcon, NDataTable } from 'naive-ui'
import { DownloadOutline, LinkOutline } from '@vicons/ionicons5'

const url = ref('')
const mode = ref<'one' | 'user'>('one')
const loadingDownloadOne = ref(false)
const loadingDownloadUser = ref(false)
const loadingParse = ref(false)
const resultOne = ref<any>(null)
const errorDownloadOne = ref('')
const errorParseOne = ref('')
const progressOne = ref('')
const directUrlOne = ref('')
const awemeId = ref('')
const desc = ref('')
const resultUser = ref<any>(null)
const errorDownloadUser = ref('')
const progressUser = ref('')
const parseUserList = ref<any[]>([])
const loadingParseUser = ref(false)
const errorParseUser = ref('')
const infoParseUser = ref('')
const showCookieInput = ref(false)
const cookieInput = ref('')
const savingCookie = ref(false)
const cookieStatus = ref<'ok'|'none'|'invalid'>('ok')
const manualCollapsed = ref(true)
const message = useMessage()

// 切换模式时只清空当前模式相关提示和 loading，保留已解析数据
watch(mode, (newMode) => {
  url.value = '' // 切换时清空输入框
  if (newMode === 'one') {
    // 清空单视频相关提示和 loading
    progressOne.value = ''
    resultOne.value = null
    errorDownloadOne.value = ''
    directUrlOne.value = ''
    errorParseOne.value = ''
    loadingDownloadOne.value = false
    loadingParse.value = false
  } else {
    // 清空主页相关提示和 loading
    progressUser.value = ''
    resultUser.value = null
    errorDownloadUser.value = ''
    errorParseUser.value = ''
    loadingDownloadUser.value = false
    loadingParseUser.value = false
  }
})

// 检查cookie有效性并联动UI
async function checkCookieStatus() {
  try {
    const res = await fetch('/douyin/check_cookie')
    const data = await res.json()
    console.log('check_cookie 返回:', data)
    if (data.code === 0) {
      cookieStatus.value = 'ok'
      showCookieInput.value = false
    } else if (data.code === 1) {
      cookieStatus.value = 'none'
      showCookieInput.value = true
    } else if (data.code === 2) {
      cookieStatus.value = 'invalid'
      showCookieInput.value = true
    } else {
      cookieStatus.value = 'none'
      showCookieInput.value = true
    }
  } catch {
    cookieStatus.value = 'none'
    showCookieInput.value = true
  }
}

onMounted(checkCookieStatus)

const handleDownload = async () => {
  if (mode.value === 'one') {
    // 先清空自身和解析直链的错误提示
    errorDownloadOne.value = ''
    errorParseOne.value = ''
    directUrlOne.value = ''
    awemeId.value = ''
    desc.value = ''
    if (!url.value || !/^https?:\/\/(www\.)?douyin\.com\//.test(url.value)) {
      errorDownloadOne.value = '请输入有效的抖音视频链接！'
      return
    }
    loadingDownloadOne.value = true
  } else {
    // 主页作品下载时校验url
    errorDownloadUser.value = ''
    errorParseUser.value = '' // 避免重复提示
    if (!url.value || !/^https?:\/\/(www\.)?douyin\.com\//.test(url.value)) {
      errorDownloadUser.value = '请输入有效的抖音视频链接！'
      return
    }
    loadingDownloadUser.value = true
  }
  try {
    let apiUrl = ''
    let params = new URLSearchParams()
    if (mode.value === 'one') {
      apiUrl = '/douyin/one_video'
      params.append('url', url.value)
    } else {
      apiUrl = '/douyin/user_post'
      params.append('url', url.value)
    }
    const res = await fetch(`${apiUrl}?${params.toString()}`)
    if (!res.body) throw new Error('无响应体')
    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let done = false
    let text = ''
    while (!done) {
      const { value, done: doneReading } = await reader.read()
      done = doneReading
      if (value) {
        let chunk = decoder.decode(value)
        // 文本替换
        chunk = chunk.replace(/开始下载作品/g, '开始解析作品')
        chunk = chunk.replace(/下载任务已触发，请到Download目录查看视频/g, '下载任务已触发，请等待下载完成')
        if (mode.value === 'one') progressOne.value += chunk
        else progressUser.value += chunk
        text += chunk
      }
    }
    // 结果区内容替换
    if (text.includes('下载任务已触发') || text.includes('全部视频已下载完成')) {
      if (mode.value === 'one') {
        // 解析完成，请等待下载完成 → 下载任务已完成，请到Download目录查看视频
        let msg = '下载任务已完成，请到Download目录查看视频'
        resultOne.value = { msg }
      } else {
        resultUser.value = { msg: '下载任务已完成，请到Download目录查看视频' }
      }
      message.success('下载信息获取成功！')
    } else if (text.includes('配置文件缺少cookie字段')) {
      if (mode.value === 'one') errorDownloadOne.value = '后端配置缺少cookie字段，无法下载。'
      else errorDownloadUser.value = '后端配置缺少cookie字段，无法下载。'
    } else {
      if (mode.value === 'one') errorDownloadOne.value = '下载未全部完成，请检查后端日志。'
      else errorDownloadUser.value = '下载未全部完成，请检查后端日志。'
    }
  } catch (e: any) {
    if (mode.value === 'one') errorDownloadOne.value = '请求失败，请检查网络或接口服务。'
    else errorDownloadUser.value = '请求失败，请检查网络或接口服务。'
  } finally {
    if (mode.value === 'one') loadingDownloadOne.value = false
    else loadingDownloadUser.value = false
  }
}

const handleParseDirect = async () => {
  // 清空下载相关和自身的错误提示
  errorParseOne.value = ''
  errorDownloadOne.value = ''
  progressOne.value = ''
  resultOne.value = null
  progressUser.value = ''
  resultUser.value = null
  errorDownloadUser.value = ''
  directUrlOne.value = ''
  awemeId.value = ''
  desc.value = ''
  loadingParse.value = true
  try {
    const apiUrl = '/douyin/parse_video'
    const params = new URLSearchParams()
    params.append('url', url.value)
    const res = await fetch(`${apiUrl}?${params.toString()}`)
    const data = await res.json()
    if (data.code === 0 && data.data && data.data.url) {
      directUrlOne.value = data.data.url
      awemeId.value = data.data.aweme_id || ''
      desc.value = data.data.desc || ''
      message.success('解析成功！')
    } else {
      const msg = data.msg || ''
      if (msg.includes('解析失败: 输入的URL不合法') || msg.includes('AwemeIdFetcher')) {
        errorParseOne.value = '请输入有效的抖音视频链接！'
      } else {
        errorParseOne.value = msg || '解析失败，请检查链接或稍后重试。'
      }
    }
  } catch (e) {
    errorParseOne.value = '请求失败，请检查网络或接口服务。'
  } finally {
    loadingParse.value = false
  }
}

// 主页批量直链解析
const handleParseUserDirect = async () => {
  errorParseUser.value = ''
  errorDownloadUser.value = '' // 避免重复提示
  if (!url.value || !/^https?:\/\/(www\.)?douyin\.com\//.test(url.value)) {
    errorParseUser.value = '请输入有效的抖音视频链接！'
    return
  }
  infoParseUser.value = '正在批量解析，请稍候...'
  parseUserList.value = []
  loadingParseUser.value = true
  try {
    const apiUrl = '/douyin/parse_user_posts'
    const params = new URLSearchParams()
    params.append('url', url.value)
    const res = await fetch(`${apiUrl}?${params.toString()}`)
    const data = await res.json()
    if (data.code === 0 && Array.isArray(data.data)) {
      parseUserList.value = data.data
      if (!data.data.length) errorParseUser.value = '未采集到任何作品，或主页无公开作品。'
      else message.success('批量解析成功！')
    } else {
      errorParseUser.value = data.msg || '批量解析失败，请检查链接或稍后重试。'
    }
    infoParseUser.value = ''
  } catch (e) {
    errorParseUser.value = '请求失败，请检查网络或接口服务。'
    infoParseUser.value = ''
  } finally {
    loadingParseUser.value = false
  }
}

function getFileNameFromUrl(url: string) {
  try {
    const name = decodeURIComponent(url.split('/').pop()?.split('?')[0] || '')
    if (name && name.endsWith('.mp4')) return name
    if (awemeId.value) return awemeId.value + '.mp4'
    return 'video.mp4'
  } catch {
    if (awemeId.value) return awemeId.value + '.mp4'
    return 'video.mp4'
  }
}

function getProxyUrl(url: string) {
  if (!url) return ''
  const params = new URLSearchParams()
  params.append('url', url)
  if (awemeId.value) params.append('aweme_id', awemeId.value)
  if (desc.value) params.append('desc', desc.value)
  return `/douyin/proxy_download?${params.toString()}`
}

async function forceDownload(url: string) {
  try {
    const res = await fetch(url, { method: 'GET' });
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await res.json();
      errorParseOne.value = data.msg || '下载失败，后端返回错误。';
      return;
    }
    // 否则用a标签下载
    const a = document.createElement('a');
    a.href = url;
    a.download = getFileNameFromUrl(url);
    a.target = '_blank';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (e) {
    errorParseOne.value = '下载失败，请检查网络或接口服务。';
  }
}

const columns = [
  { title: '标题', key: 'desc', ellipsis: { tooltip: true }, width: 240 },
  {
    title: '操作',
    key: 'url',
    width: 90,
    render(row: any) {
      if (!row.url) return '无直链'
      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          onClick: () => forceDownload(getProxyUrlUser(row))
        },
        { default: () => '下载' }
      )
    }
  }
]

function getProxyUrlUser(row: any) {
  const params = new URLSearchParams()
  params.append('url', row.url)
  if (row.aweme_id) params.append('aweme_id', row.aweme_id)
  if (row.desc) params.append('desc', row.desc)
  return `/douyin/proxy_download?${params.toString()}`
}

function cancelCookieInput() {
  showCookieInput.value = false
  cookieInput.value = ''
}

async function saveCookie() {
  if (!cookieInput.value.trim()) {
    message.error('Cookie不能为空！')
    return
  }
  savingCookie.value = true
  try {
    const res = await fetch('/douyin/set_cookie', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookie: cookieInput.value.trim() })
    })
    const data = await res.json()
    if (data.code === 0) {
      message.success('Cookie配置成功！')
      await checkCookieStatus() // 保存后自动检测并刷新UI
      // 强制刷新UI
      window.location.reload()
    } else {
      message.error(data.msg || 'Cookie配置失败')
    }
  } catch (e) {
    message.error('网络错误，Cookie配置失败')
  } finally {
    savingCookie.value = false
  }
}
</script>

<style scoped>
.anydownload-header-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  gap: 18px;
}
.anydownload-logo {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  box-shadow: 0 2px 8px #00000022;
}
.anydownload-title-gradient {
  font-size: 2.4rem;
  font-weight: 900;
  background: linear-gradient(270deg, #4dd0e1, #00bcd4, #42e695, #f9d423, #fc913a, #ff4e50, #4dd0e1);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-fill-color: transparent;
  letter-spacing: 6px;
  text-shadow: 0 2px 12px #00000033, 0 1px 0 #fff2;
  font-family: 'Segoe UI', 'Arial', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  line-height: 1.1;
  animation: gradient-move 3s linear infinite;
}
@keyframes gradient-move {
  0% {
    background-position: 0% 50%;
  }
  100% {
    background-position: 100% 50%;
  }
}
.douyin-downloader {
  width: 720px;
  max-width: 90vw;
  min-width: 420px;
  padding: 40px 32px 32px 32px;
  margin: 48px auto;
  background: rgba(30, 30, 30, 0.97);
  color: #fff;
  box-shadow: 0 4px 24px 0 #00000033;
  font-size: 17px;
  border-radius: 18px;
}
.styled-input {
  height: 48px;
  font-size: 17px;
  border-radius: 10px;
  margin: 24px 0 36px 0;
  background: #232323;
  color: #fff;
  border: 1.5px solid #444;
  box-shadow: 0 1px 4px 0 #00000018;
  width: 100%;
  max-width: none;
}
.input-url {
  margin: 0 auto;
  display: block;
  width: 100%;
  align-items: center;
  height: 48px;
  line-height: 48px;
}
.download-btn {
  min-width: 130px !important;
  font-size: 16px !important;
  height: 46px !important;
  padding: 0 28px !important;
  border-radius: 9px !important;
  box-sizing: border-box !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.mode-group {
  margin-bottom: 18px;
  font-size: 17px;
}
.result-alert {
  margin-top: 18px;
  font-size: 16px;
  width: 100%;
  margin-left: 0;
  margin-right: 0;
}
/* 修复 n-alert 图标和首行文字对齐 */
:deep(.n-alert__body) {
  display: flex;
  align-items: center;
}
:deep(.n-alert__icon) {
  align-items: center !important;
}
:deep(.n-alert__title),
:deep(.n-alert__content) {
  display: flex;
  align-items: center;
}
/* 进度区每条信息最多两行，超出省略号，不要滚动条 */
.progress-line {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: normal;
  word-break: break-all;
  margin-bottom: 2px;
  line-height: 1.5;
  font-size: 15px;
}
.button-group {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
  justify-content: center;
  margin-top: 36px;
}
.mt-2 {
  margin-top: 24px;
  width: 100%;
  margin-left: 0;
  margin-right: 0;
}
/* 关键：让n-input内部input区域最大化 */
:deep(.n-input) {
  width: 100% !important;
  display: flex !important;
  align-items: center !important;
}
:deep(.n-input-wrapper) {
  width: 100% !important;
  display: flex !important;
  align-items: center !important;
}
:deep(.n-input__input-el) {
  flex: 1 1 0 !important;
  min-width: 0 !important;
  width: 100% !important;
  box-sizing: border-box !important;
  padding: 0 8px !important;
  background: transparent !important;
  color: #fff !important;
  font-size: 17px !important;
  height: 48px !important;
  line-height: 48px !important;
  display: flex !important;
  align-items: center !important;
  padding-right: 16px !important;
}
:deep(.n-input__suffix) {
  right: 0 !important;
  position: absolute !important;
  top: 0;
  height: 100%;
  display: flex;
  align-items: center;
  background: transparent;
  z-index: 2;
  padding-right: 8px;
}
:deep(.n-input__suffix .n-base-clear) {
  margin: 0 !important;
  position: static !important;
  display: flex;
  align-items: center;
  height: 100%;
}
/* 表格操作列居中且更窄 */
:deep(.n-data-table-th--key-url),
:deep(.n-data-table-td--key-url) {
  text-align: center !important;
  justify-content: center !important;
  align-items: center !important;
}
.cookie-alert {
  font-size: 16px;
  font-weight: bold;
  text-align: center;
}
.cookie-manual {
  max-width: 720px;
  margin: 32px auto 0 auto;
  background: transparent;
  border-radius: 12px;
  padding: 28px 32px 18px 32px;
  color: #eee;
  font-size: 16px;
  box-shadow: 0 2px 12px 0 #00000022;
  text-align: left;
}
.manual-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 12px;
  color: #4dd0e1;
  text-align: left;
}
.manual-list {
  margin: 0 0 10px 18px;
  padding: 0;
  text-align: left;
}
.manual-list li {
  margin-bottom: 8px;
  line-height: 1.7;
  text-align: left;
}
.manual-tip {
  color: #ffb300;
  font-size: 15px;
  margin-top: 10px;
  text-align: left;
}
.cookie-btn-row {
  width: 100%;
  text-align: right;
  margin-top: 48px;
  margin-bottom: 8px;
}
.cookie-input-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.cookie-btns {
  display: flex;
  flex-direction: row;
  gap: 10px;
  align-items: flex-start;
}
.cookie-input-center :deep(textarea) {
  text-align: center;
}
.cookie-tip-text {
  color: #aaa;
  font-size: 14px;
  margin-top: 6px;
  margin-left: 2px;
  text-align: left;
}
</style>
