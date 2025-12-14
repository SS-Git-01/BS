<template>
  <div id="app">
    <van-nav-bar title="我的云相册" fixed placeholder z-index="999" />

    <div v-if="!token" class="auth-container">
      <div class="logo-area">
        <h1>📸</h1>
        <p>记录美好瞬间</p>
      </div>
      <van-tabs v-model:active="activeTab" type="card">
        <van-tab title="登录">
          <van-form @submit="onLogin" class="form-box">
            <van-cell-group inset>
              <van-field v-model="loginForm.username" name="username" label="用户名" placeholder="请输入用户名" />
              <van-field v-model="loginForm.password" type="password" name="password" label="密码" placeholder="请输入密码" />
            </van-cell-group>
            <div style="margin: 24px 16px;">
              <van-button round block type="primary" native-type="submit">立即登录</van-button>
            </div>
          </van-form>
        </van-tab>
        <van-tab title="注册">
          <van-form @submit="onRegister" class="form-box">
            <van-cell-group inset>
              <van-field v-model="registerForm.username" name="username" label="用户名" placeholder="设置用户名" />
              <van-field v-model="registerForm.email" name="email" label="邮箱" placeholder="常用邮箱" />
              <van-field v-model="registerForm.password" type="password" name="password" label="密码" placeholder="设置密码" />
            </van-cell-group>
            <div style="margin: 24px 16px;">
              <van-button round block type="success" native-type="submit">注册账号</van-button>
            </div>
          </van-form>
        </van-tab>
      </van-tabs>
    </div>

    <div v-else class="main-content">
      <van-cell-group inset title="上传新照片">
        <div class="upload-box">
          <van-uploader :after-read="afterRead" v-model="fileList" :max-count="1" upload-text="点击上传" />
          <p class="tip-text">支持自动提取拍摄时间与地点 (Exif)</p>
        </div>
      </van-cell-group>

      <van-divider>我的照片库 ({{ images.length }} 张)</van-divider>
      <van-empty v-if="images.length === 0" description="还没有照片，快去上传一张吧！" />

      <van-grid :column-num="2" gutter="10" class="image-grid">
        <van-grid-item v-for="(img, index) in images" :key="img.id" class="grid-item-wrapper">
          <van-image
            class="hover-scale-img"
            :src="getImageUrl(img.filename)" 
            height="150" 
            fit="cover"
            @click="openPreview(index)" 
          />
          
          <div class="delete-btn" @click.stop="confirmDelete(img)">
            <van-icon name="delete-o" />
          </div>

          <div class="image-info">
            <div class="info-row">📅 {{ formatDate(img.capture_date) }}</div>
            <div class="info-row" v-if="img.device && img.device !== 'Unknown'">📱 {{ img.device }}</div>
            <div class="info-row" v-if="img.location && img.location !== 'Unknown'">📍 {{ img.location }}</div>
          </div>
        </van-grid-item>
      </van-grid>

      <div style="margin: 30px 20px;">
        <van-button type="danger" block round plain @click="logout">退出登录</van-button>
      </div>

      <van-image-preview
        v-model:show="showPreview"
        :images="previewImages"
        :start-position="previewIndex"
        :closeable="true"
        close-icon-position="top-right"
        @change="onChange"
        ref="previewRef"
      >
        <template #cover v-if="isPC">
          <div class="nav-btn left" @click.stop="prevImage">
            <van-icon name="arrow-left" />
          </div>
          <div class="nav-btn right" @click.stop="nextImage">
            <van-icon name="arrow" />
          </div>
          <div class="zoom-tip">🖱️ 滚轮缩放 | ⬅️➡️ 切换</div>
        </template>
      </van-image-preview>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import axios from 'axios';
// ✅ 修复：合并所有 Vant 组件引用到这一行
import { showToast, showSuccessToast, showFailToast, showConfirmDialog } from 'vant';

const token = ref(localStorage.getItem('token') || '');
const activeTab = ref(0);
const loginForm = ref({ username: '', password: '' });
const registerForm = ref({ username: '', email: '', password: '' });
const fileList = ref([]);
const images = ref([]);

const hostname = window.location.hostname; 
const API_BASE = `http://${hostname}:5000/api`;
const IMG_BASE = `http://${hostname}:5000/uploads/`;

const showPreview = ref(false);
const previewIndex = ref(0);
const previewRef = ref(null);
const currentZoom = ref(1); 

const isPC = ref(!/Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent));

const previewImages = computed(() => images.value.map(img => IMG_BASE + img.filename));

const formatDate = (dateStr) => {
  if (!dateStr) return '未知时间';
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute:'2-digit' });
};
const getImageUrl = (filename) => IMG_BASE + filename;

const openPreview = (index) => {
  previewIndex.value = index;
  showPreview.value = true;
  currentZoom.value = 1; 
  
  nextTick(() => {
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('wheel', handleWheel, { passive: false });
  });
};

const resetZoom = () => {
  currentZoom.value = 1;
  const allImages = document.querySelectorAll('.van-image-preview__image');
  allImages.forEach(img => {
    img.style.transform = ''; 
    img.style.transition = 'transform 0.3s ease-out';
  });
};

const onChange = (newIndex) => {
  previewIndex.value = newIndex;
  resetZoom(); 
};

const prevImage = () => {
  if (previewRef.value) {
    const newIndex = (previewIndex.value - 1 + images.value.length) % images.value.length;
    previewRef.value.swipeTo(newIndex);
  }
};

const nextImage = () => {
  if (previewRef.value) {
    const newIndex = (previewIndex.value + 1) % images.value.length;
    previewRef.value.swipeTo(newIndex);
  }
};

const handleKeyDown = (e) => {
  if (!showPreview.value) return;
  switch (e.key) {
    case 'Escape': showPreview.value = false; break;
    case 'ArrowLeft': prevImage(); break;
    case 'ArrowRight': nextImage(); break;
  }
};

const handleWheel = (e) => {
  if (!showPreview.value) return;
  
  e.preventDefault();
  
  const ZOOM_SPEED = 0.001; 
  let newZoom = currentZoom.value - e.deltaY * ZOOM_SPEED;
  
  if (newZoom < 0.5) newZoom = 0.5;
  if (newZoom > 5) newZoom = 5;
  
  currentZoom.value = newZoom;
  
  const allImages = document.querySelectorAll('.van-image-preview__swipe .van-image-preview__image');
  const currentImg = allImages[previewIndex.value];

  if (currentImg) {
    currentImg.style.transition = 'none'; 
    currentImg.style.transform = `scale(${newZoom})`;
  }
};

watch(showPreview, (val) => {
  if (!val) {
    window.removeEventListener('keydown', handleKeyDown);
    window.removeEventListener('wheel', handleWheel);
  }
});

const fetchImages = async () => {
  if (!token.value) return;
  try {
    const res = await axios.get(`${API_BASE}/images`, { headers: { 'Authorization': `Bearer ${token.value}` } });
    images.value = res.data;
  } catch (err) { if (err.response && err.response.status === 401) logout(); }
};

// ✨ 新增：删除功能逻辑
const confirmDelete = (img) => {
  showConfirmDialog({
    title: '确认删除',
    message: '删除后无法恢复，确定要删除这张照片吗？',
  })
    .then(async () => {
      try {
        await axios.delete(`${API_BASE}/images/${img.id}`, {
          headers: { 'Authorization': `Bearer ${token.value}` }
        });
        showSuccessToast('删除成功');
        fetchImages();
      } catch (err) {
        showFailToast('删除失败');
      }
    })
    .catch(() => {});
};

const afterRead = async (file) => {
  file.status = 'uploading';
  const formData = new FormData();
  formData.append('file', file.file);
  try {
    await axios.post(`${API_BASE}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data', 'Authorization': `Bearer ${token.value}` }
    });
    file.status = 'done';
    showSuccessToast('上传成功！');
    setTimeout(() => { fileList.value = []; }, 1000);
    fetchImages();
  } catch (err) { file.status = 'failed'; showFailToast('上传失败'); }
};

const onLogin = async (values) => {
  try {
    const res = await axios.post(`${API_BASE}/auth/login`, values);
    token.value = res.data.token;
    localStorage.setItem('token', res.data.token);
    showSuccessToast('登录成功');
    fetchImages();
  } catch (err) { showFailToast(err.response?.data?.message || '登录失败'); }
};

const onRegister = async (values) => {
  try { await axios.post(`${API_BASE}/auth/register`, values); showSuccessToast('注册成功'); activeTab.value = 0; }
  catch (err) { showFailToast('注册失败'); }
};

const logout = () => { token.value = ''; localStorage.removeItem('token'); images.value = []; };

onMounted(() => { if (token.value) fetchImages(); });
</script>

<style scoped>
.auth-container { padding: 40px 20px; text-align: center; }
.logo-area { margin-bottom: 40px; }
.logo-area h1 { font-size: 60px; margin: 0; }
.main-content { padding-bottom: 50px; background-color: #f7f8fa; min-height: 100vh; }
.upload-box { text-align: center; padding: 20px; background: #fff; }
.tip-text { font-size: 12px; color: #996; margin-top: 8px; }
.image-grid { padding: 10px; }
.image-info { padding: 8px; font-size: 12px; color: #333; background: #fff; width: 100%; }
.info-row { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 4px; }

/* 必须给父容器相对定位，删除按钮才能定位 */
.grid-item-wrapper {
  position: relative;
}

/* 删除按钮样式 */
.delete-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 24px;
  height: 24px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 4px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s;
}
.delete-btn:hover {
  background: rgba(255, 0, 0, 0.8);
}

.nav-btn {
  position: fixed; 
  top: 50%;
  transform: translateY(-50%);
  width: 56px;
  height: 56px;
  background-color: rgba(30, 30, 30, 0.4); 
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 32px;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 9999;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255,255,255,0.1);
  user-select: none;
}

.nav-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-50%) scale(1.1);
}

.nav-btn:active {
  transform: translateY(-50%) scale(0.95);
}

.nav-btn.left { left: 40px; }
.nav-btn.right { right: 40px; }

.zoom-tip {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255, 255, 255, 0.7);
  background: rgba(0, 0, 0, 0.5);
  padding: 5px 15px;
  border-radius: 20px;
  font-size: 12px;
  pointer-events: none;
  z-index: 9999;
}

@media (hover: hover) and (pointer: fine) {
  .hover-scale-img >>> .van-image__img {
    transition: transform 0.3s ease;
  }
  .hover-scale-img:hover >>> .van-image__img {
    transform: scale(1.1);
  }
}
</style>