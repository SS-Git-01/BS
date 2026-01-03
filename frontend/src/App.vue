<template>
  <van-config-provider :theme="theme" class="app-provider">
    <div id="app">
      <div v-if="!token" class="login-bg">
        <div class="login-card">
          <div class="login-theme-switch" @click="toggleTheme">
            <span>{{ theme === 'dark' ? '🌙 深色模式' : '☀️ 浅色模式' }}</span>
          </div>
          <div class="login-header">
            <div class="login-logo">📸</div>
            <h3>图片管理网站</h3>
          </div>
          
          <van-tabs v-model:active="activeTab" animated swipeable color="#00AEEC" title-active-color="#00AEEC" background="transparent" line-width="30px">
            <van-tab title="登录">
              <van-form @submit="onLogin" class="auth-form">
                <div class="form-item">
                  <van-field 
                    v-model="loginForm.username" 
                    name="username" 
                    placeholder="请输入账号" 
                    :border="false"
                    class="custom-input"
                  >
                    <template #left-icon>
                      <van-icon name="manager" class="input-icon" />
                    </template>
                  </van-field>
                </div>
                <div class="form-item">
                  <van-field 
                    v-model="loginForm.password" 
                    type="password" 
                    name="password" 
                    placeholder="请输入密码" 
                    :border="false"
                    class="custom-input"
                  >
                    <template #left-icon>
                      <van-icon name="lock" class="input-icon" />
                    </template>
                  </van-field>
                </div>
                <div class="btn-area">
                  <van-button round block color="#00AEEC" native-type="submit">登 录</van-button>
                </div>
              </van-form>
            </van-tab>
            
            <van-tab title="注册">
              <van-form @submit="onRegister" class="auth-form">
                <div class="form-item">
                  <van-field 
                    v-model="registerForm.username" 
                    name="username" 
                    placeholder="用户名" 
                    :border="false"
                    class="custom-input"
                  />
                </div>
                <div class="form-item">
                  <van-field 
                    v-model="registerForm.email" 
                    name="email" 
                    placeholder="电子邮箱" 
                    :border="false"
                    class="custom-input"
                  />
                </div>
                <div class="form-item">
                  <van-field 
                    v-model="registerForm.password" 
                    type="password" 
                    name="password" 
                    placeholder="密码" 
                    :border="false"
                    class="custom-input"
                  />
                </div>
                <div class="btn-area">
                  <van-button round block type="success" native-type="submit">注 册</van-button>
                </div>
              </van-form>
            </van-tab>
          </van-tabs>
        </div>
      </div>

      <div v-else class="main-content">
        
        <van-sticky>
          <div class="custom-header">
            <div class="header-left">
              <span class="header-title">图片管理网站</span>
            </div>

            <div class="header-right">
              <div class="theme-btn-inline" @click="toggleTheme">
                <span class="theme-content">
                  {{ theme === 'dark' ? '🌙 深色模式' : '☀️ 浅色模式' }}
                </span>
              </div>
              <div class="search-group">
                <van-search 
                  v-model="searchQuery" 
                  shape="round"
                  background="transparent"
                  placeholder="搜索..." 
                  class="header-search"
                  left-icon=""
                  :clearable="false"
                  @search="onSearch"
                />
                <van-button 
                  type="primary" 
                  class="search-btn"
                  icon="search" 
                  @click="onSearch"
                >
                </van-button>
                <div v-if="searchQuery" class="search-clear" @click="onClear">
                  <van-icon name="clear" />
                </div>
              </div>

              <div class="header-actions">
                <van-uploader 
                  :after-read="afterRead" 
                  v-model="fileList" 
                  multiple 
                  :max-count="9" 
                  accept="image/*"
                  class="header-uploader"
                  :preview-image="false"
                >
                  <van-button type="primary" size="small" round class="action-btn upload-btn">
                    <span class="btn-text">上传照片</span>
                  </van-button>
                </van-uploader>

                <van-button size="small" round class="action-btn logout-btn" @click="logout">
                  <span class="btn-text">退出登录</span>
                </van-button>
              </div>
            </div>
          </div>
        </van-sticky>

        <van-list
          v-model:loading="loading"
          :finished="finished"
          finished-text="没有更多了"
          @load="onLoad"
          style="margin-top: 16px;" 
        >
          <van-empty v-if="images.length === 0 && !loading" description="没有找到照片哦~" />

          <div class="masonry-layout">
            <div v-for="(img, index) in images" :key="img.id" class="pin-card" @click="openPreview(index)">
              
              <div class="pin-image-wrapper">
                <img :src="getImageUrl(img.thumbnail || img.filename)" :alt="img.filename" loading="lazy" />
                
                <div class="pin-overlay">
                  <button class="pin-btn edit" @click.stop="openEditor(img)">
                    <van-icon name="edit" />
                  </button>
                  <button class="pin-btn del" @click.stop="confirmDelete(img)">
                    <van-icon name="delete-o" />
                  </button>
                </div>
              </div>

              <div class="pin-info">
                <div class="pin-tags" v-if="img.ai_tags && img.ai_tags.length">
                  <span v-for="(tag, tIndex) in img.ai_tags.slice(0, 3)" :key="'a'+tIndex" class="tag-pill ai">
                    {{ tag.label }}
                  </span>
                </div>

                <div class="pin-tags user-tags-area">
                  <span 
                    v-for="(tag, tIndex) in img.tags" 
                    :key="'u'+tIndex" 
                    class="tag-pill user"
                  >
                    {{ tag }}
                    <van-icon name="cross" class="tag-close" @click.stop="handleRemoveTag(img, tag)" />
                  </span>
                  <span class="tag-add-btn" @click.stop="openAddTagDialog(img)">+</span>
                </div>
                
                <div class="pin-detail-list">
                  <div class="detail-row" v-if="img.location && img.location !== 'Unknown'">
                    <van-icon name="location-o" />
                    <span>{{ img.location }}</span>
                  </div>
                  <div class="detail-row">
                    <van-icon name="calendar-o" />
                    <span>{{ formatDate(img.capture_date).split(' ')[0] }}</span>
                  </div>
                  <div class="detail-row" v-if="img.resolution && img.resolution !== '未知'">
                    <van-icon name="photo-o" />
                    <span>{{ img.resolution }}</span>
                  </div>
                  <div class="detail-row" v-if="img.device && img.device !== 'Unknown'">
                    <van-icon name="desktop-o" />
                    <span>{{ img.device }}</span>
                  </div>
                </div>

              </div>

            </div>
          </div>
        </van-list>

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

        <van-dialog 
          v-model:show="showAddTagDialog" 
          title="添加标签" 
          show-cancel-button
          @confirm="submitAddTag"
        >
          <van-cell-group inset style="margin: 20px 0;">
            <van-field
              v-model="newTagName"
              placeholder="请输入标签名"
              border
              clearable
            />
          </van-cell-group>
        </van-dialog>

        <van-dialog
          v-model:show="showEditDialog"
          title="图片编辑"
          show-cancel-button
          confirm-button-text="保存修改"
          @confirm="submitEdit"
          :width="isPC ? '1000px' : '90%'"
        >
          <div class="editor-container" :style="{ '--b': editParams.brightness, '--c': editParams.contrast }">
            <div class="cropper-stage">
              <div class="cropper-box" @wheel.prevent="onEditorWheel">
                <img 
                  ref="editorImageRef" 
                  :src="currentEditingImage ? getImageUrl(currentEditingImage.filename) : ''" 
                />
              </div>
            </div>

            <div class="controls-area">
              <div class="control-row">
                <span>旋转:</span>
                <van-button size="small" icon="replay" round @click="rotateImage">90°</van-button>
              </div>
              <div class="control-row">
                <span>亮度:</span>
                <van-slider v-model="editParams.brightness" :min="0.5" :max="1.5" :step="0.1" style="width: 70%" active-color="#1989fa" />
              </div>
              <div class="control-row">
                <span>对比:</span>
                <van-slider v-model="editParams.contrast" :min="0.5" :max="1.5" :step="0.1" style="width: 70%" active-color="#1989fa" />
              </div>
            </div>
          </div>
        </van-dialog>
      </div>
    </div>
  </van-config-provider>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import axios from 'axios';
import { showToast, showSuccessToast, showFailToast, showConfirmDialog } from 'vant';

const theme = ref(localStorage.getItem('theme') || 'light');
const toggleTheme = () => {
  theme.value = theme.value === 'light' ? 'dark' : 'light';
  localStorage.setItem('theme', theme.value);
};

const token = ref(localStorage.getItem('token') || '');
const activeTab = ref(0);
const loginForm = ref({ username: '', password: '' });
const registerForm = ref({ username: '', email: '', password: '' });
const fileList = ref([]);
const images = ref([]);

const searchQuery = ref('');

const loading = ref(false);
const finished = ref(false);
const page = ref(1);

const hostname = window.location.hostname; 
const API_BASE = `http://${hostname}:5000/api`;
const IMG_BASE = `http://${hostname}:5000/uploads/`;

const showPreview = ref(false);
const previewIndex = ref(0);
const previewRef = ref(null);
const currentZoom = ref(1); 
const isPC = ref(!/Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent));
const previewImages = computed(() => images.value.map(img => getImageUrl(img.filename)));

const showAddTagDialog = ref(false);
const newTagName = ref('');
const currentEditingImage = ref(null);

const showEditDialog = ref(false);
const editorImageRef = ref(null);
let cropper = null;
const editParams = ref({
  rotate: 0,
  brightness: 1.0,
  contrast: 1.0
});

const getImageUrl = (filename) => {
  if (filename && filename.startsWith('blob:')) return filename;
  return IMG_BASE + filename;
};

const onLoad = async () => {
  if (!token.value) return;
  
  try {
    const res = await axios.get(`${API_BASE}/images`, { 
      params: { 
        q: searchQuery.value,
        page: page.value,
        limit: 10 
      }, 
      headers: { 'Authorization': `Bearer ${token.value}` } 
    });
    
    if (res.data.items) {
      images.value.push(...res.data.items);
    }
    
    page.value++;
    loading.value = false;
    
    if (!res.data.has_next) {
      finished.value = true;
    }
  } catch (err) {
    loading.value = false;
    finished.value = true;
    if (err.response && err.response.status === 401) logout();
  }
};

const resetList = () => {
  page.value = 1;
  images.value = [];
  finished.value = false;
  loading.value = true; 
  onLoad(); 
};

const onSearch = () => {
  resetList(); 
};

const onClear = () => {
  searchQuery.value = '';
};

const formatDate = (dateStr) => {
  if (!dateStr) return '未知时间';
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute:'2-digit' });
};

const openPreview = (index) => {
  previewIndex.value = index;
  showPreview.value = true;
  currentZoom.value = 1; 
  nextTick(() => {
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('wheel', handleWheel, { passive: false });
    setTimeout(() => {
        resetZoom();
    }, 50);
  });
};

const resetZoom = () => {
  currentZoom.value = 1;
  const allImages = document.querySelectorAll('.van-image-preview__swipe img');
  allImages.forEach(img => {
      img.style.transform = 'scale(1) translate(0, 0)';
      img.style.transition = 'transform 0.3s ease-out';
  });
};

const onChange = (newIndex) => { previewIndex.value = newIndex; resetZoom(); };

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

  const items = document.querySelectorAll('.van-image-preview__swipe .van-swipe-item');
  const screenCenter = window.innerWidth / 2;
  let currentImg = null;

  for (const item of items) {
    const rect = item.getBoundingClientRect();
    if (rect.left <= screenCenter && rect.right >= screenCenter) {
      currentImg = item.querySelector('img');
      break;
    }
  }

  if (currentImg) {
    currentImg.style.transition = 'none'; 
    currentImg.style.transform = `scale(${newZoom}) translate(0, 0)`; 
  }
};

watch(showPreview, (val) => { 
  if (!val) { 
    window.removeEventListener('keydown', handleKeyDown); 
    window.removeEventListener('wheel', handleWheel); 
  } 
});

const confirmDelete = (img) => {
  showConfirmDialog({ title: '确认删除', message: '删除后无法恢复，确定要删除这张照片吗？' })
    .then(async () => {
      try {
        await axios.delete(`${API_BASE}/images/${img.id}`, { headers: { 'Authorization': `Bearer ${token.value}` } });
        showSuccessToast('删除成功');
        const idx = images.value.findIndex(i => i.id === img.id);
        if (idx !== -1) images.value.splice(idx, 1);
      } catch (err) { showFailToast('删除失败'); }
    }).catch(() => {});
};

const pollImageStatus = (imageId) => {
  let attempts = 0;
  const maxAttempts = 10; 
  
  const interval = setInterval(async () => {
    attempts++;
    try {
      const res = await axios.get(`${API_BASE}/images/${imageId}`, {
        headers: { 'Authorization': `Bearer ${token.value}` }
      });
      
      const imgData = res.data;
      
      if (imgData.ai_tags && imgData.ai_tags.length > 0) {
        clearInterval(interval);
        
        const targetImg = images.value.find(i => i.id === imageId);
        if (targetImg) {
          targetImg.ai_tags = imgData.ai_tags;
          showSuccessToast('AI 分析完成！');
        }
      } else {
        console.log(`Waiting for AI... Attempt ${attempts}`);
      }
      
      if (attempts >= maxAttempts) {
        clearInterval(interval);
        console.log('Stop polling (timeout)');
      }
      
    } catch (err) {
      clearInterval(interval); 
    }
  }, 2000); 
};

const uploadOneFile = async (item) => {
  item.status = 'uploading';
  item.message = '上传中...';

  const formData = new FormData();
  formData.append('file', item.file);

  try {
    const res = await axios.post(`${API_BASE}/upload`, formData, { 
      headers: { 
        'Content-Type': 'multipart/form-data', 
        'Authorization': `Bearer ${token.value}` 
      } 
    });
    
    item.status = 'done';
    item.message = '成功';
    
    const placeholderImg = images.value.find(img => img.isTemp && img.filename === item.objectUrl);
    if (placeholderImg) {
      placeholderImg.id = res.data.id;
      placeholderImg.filename = res.data.filename;
      placeholderImg.thumbnail = res.data.thumbnail;
      placeholderImg.device = res.data.device;
      placeholderImg.location = res.data.location;
      placeholderImg.resolution = res.data.resolution;
      placeholderImg.capture_date = res.data.capture_date;
      placeholderImg.isTemp = false;
      pollImageStatus(res.data.id);
    }
    
  } catch (err) {
    item.status = 'failed';
    item.message = '失败';
    showFailToast('部分图片上传失败');
    const idx = images.value.findIndex(img => img.isTemp && img.filename === item.objectUrl);
    if (idx !== -1) images.value.splice(idx, 1);
  }
};

const afterRead = async (items) => {
  const files = Array.isArray(items) ? items : [items];
  
  files.forEach(fileItem => {
    if (!fileItem.objectUrl) {
      fileItem.objectUrl = URL.createObjectURL(fileItem.file);
    }
    images.value.push({
      id: `temp-${Date.now()}-${Math.random()}`,
      filename: fileItem.objectUrl,
      thumbnail: fileItem.objectUrl,
      tags: [],
      ai_tags: [{ label: '上传中...' }],
      isTemp: true
    });
  });

  await Promise.all(files.map(file => uploadOneFile(file)));
  setTimeout(() => {
    fileList.value = fileList.value.filter(item => item.status === 'failed');
    if (fileList.value.length === 0) {
      showSuccessToast('所有上传完成');
    }
  }, 1000);
};

const onLogin = async (values) => {
  try {
    const res = await axios.post(`${API_BASE}/auth/login`, values);
    token.value = res.data.token;
    localStorage.setItem('token', res.data.token);
    showSuccessToast(res.data.message || '登录成功');
    resetList(); 
  } catch (err) { 
    showFailToast(err.response?.data?.message || '登录失败'); 
  }
};

const onRegister = async (values) => { 
  try { 
    await axios.post(`${API_BASE}/auth/register`, values); 
    showSuccessToast('注册成功'); 
    activeTab.value = 0; 
  } catch (err) { 
    showFailToast(err.response?.data?.message || '注册失败'); 
  } 
};

const logout = () => { token.value = ''; localStorage.removeItem('token'); images.value = []; };

const openAddTagDialog = (img) => {
  currentEditingImage.value = img;
  newTagName.value = '';
  showAddTagDialog.value = true;
};

const submitAddTag = async () => {
  if (!newTagName.value.trim() || !currentEditingImage.value) return;
  try {
    await axios.post(`${API_BASE}/tags`, {
      image_id: currentEditingImage.value.id,
      tag_name: newTagName.value.trim()
    }, { 
      headers: { 'Authorization': `Bearer ${token.value}` } 
    });
    
    if (!currentEditingImage.value.tags) {
      currentEditingImage.value.tags = [];
    }
    if (!currentEditingImage.value.tags.includes(newTagName.value.trim())) {
      currentEditingImage.value.tags.push(newTagName.value.trim());
    }
    showSuccessToast('标签添加成功');
  } catch (err) {
    showFailToast('添加失败');
  }
};

const handleRemoveTag = async (img, tagToRemove) => {
  try {
    await axios.delete(`${API_BASE}/tags`, {
      data: {
        image_id: img.id,
        tag_name: tagToRemove
      },
      headers: { 'Authorization': `Bearer ${token.value}` }
    });

    const index = img.tags.indexOf(tagToRemove);
    if (index > -1) {
      img.tags.splice(index, 1);
    }
    showSuccessToast('标签已删除');
  } catch (err) {
    showFailToast('删除失败');
  }
};

const openEditor = (img) => {
  currentEditingImage.value = img;
  editParams.value = { rotate: 0, brightness: 1.0, contrast: 1.0 };
  showEditDialog.value = true;
};

const initCropper = () => {
  nextTick(() => {
    if (editorImageRef.value) {
      if (cropper) {
        cropper.destroy();
      }
      const Cropper = window.Cropper;
      cropper = new Cropper(editorImageRef.value, {
        viewMode: 0, 
        dragMode: 'move', 
        autoCropArea: 0.8,
        restore: false,
        modal: true,
        guides: true,
        center: true,
        highlight: false,
        cropBoxMovable: true,
        cropBoxResizable: true,
        toggleDragModeOnDblclick: false,
        background: false, 
        checkOrientation: false,
        zoomOnWheel: false, 
      });
    }
  });
};

const onEditorWheel = (e) => {
  if (!cropper) return;
  const ratio = e.deltaY > 0 ? -0.1 : 0.1;
  cropper.zoom(ratio);
};

const rotateImage = () => {
  if (cropper) {
    cropper.rotate(90);
    editParams.value.rotate += 90;
  }
};

const submitEdit = async () => {
  if (!cropper || !currentEditingImage.value) return;

  const cropData = cropper.getData(); 

  try {
    const res = await axios.put(`${API_BASE}/images/${currentEditingImage.value.id}/edit`, {
      crop: {
        x: cropData.x,
        y: cropData.y,
        width: cropData.width,
        height: cropData.height
      },
      rotate: editParams.value.rotate, 
      brightness: editParams.value.brightness,
      contrast: editParams.value.contrast
    }, {
      headers: { 'Authorization': `Bearer ${token.value}` }
    });

    showSuccessToast('编辑成功');
    showEditDialog.value = false;
    const timestamp = new Date().getTime();
    
    const targetImg = images.value.find(i => i.id === currentEditingImage.value.id);
    
    if (targetImg) {
      const rawFilename = targetImg.filename.split('?')[0];
      targetImg.filename = `${rawFilename}?t=${timestamp}`;
      
      if (targetImg.thumbnail) {
         const rawThumb = targetImg.thumbnail.split('?')[0];
         targetImg.thumbnail = `${rawThumb}?t=${timestamp}`;
      }
      targetImg.resolution = res.data.resolution;
      targetImg.device = res.data.device;         
      targetImg.location = res.data.location;     
      targetImg.capture_date = res.data.capture_date; 
    }

  } catch (err) {
    showFailToast('编辑失败');
    console.error(err);
  }
};

watch(showEditDialog, (val) => {
  if (val) {
    initCropper();
  } else {
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
  }
});

onMounted(() => { 
  if (token.value) {
  }
});
</script>

<style>
:root {
  --app-bg: #fff;
  --card-bg: rgba(255, 255, 255, 0.96);
  --pin-card-bg: #ffffff;
  --header-bg: rgba(255, 255, 255, 0.95);
  --search-inner-bg: transparent; 
  --text-main: #333;
  --text-secondary: #888;
  --text-header: #333;
  --border-color: #ebedf0;
  --login-gradient: linear-gradient(135deg, #f0f2f5 0%, #dbe9f6 100%);
  --card-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
  --tag-ai-bg: #f0f0f0;
  --tag-ai-text: #111;
  --tag-user-bg: #e6f7ff;
  --input-icon-color: #c0c0c0;
  --search-bar-gray: #f0f1f2;
  --cropper-stage-bg: #ebedf0;
}

.van-theme-dark {
  --app-bg: #121212;
  --card-bg: #1e1e1e;
  --pin-card-bg: #1e1e1e;
  --header-bg: rgba(30, 30, 30, 0.95);
  --search-inner-bg: transparent;
  --text-main: #f5f5f5;
  --text-secondary: #707070;
  --text-header: #f5f5f5;
  --border-color: #333;
  --login-gradient: linear-gradient(135deg, #1a1a1a 0%, #2c3e50 100%);
  --card-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  --tag-ai-bg: #333;
  --tag-ai-text: #ccc;
  --tag-user-bg: #1a2a3a;
  --input-icon-color: #666;
  --search-bar-gray: rgba(255, 255, 255, 0.1);
  --cropper-stage-bg: #333333;
}

body {
  background-color: var(--app-bg);
  color: var(--text-main);
  transition: background-color 0.3s, color 0.3s;
}

.header-search .van-search__content {
  background-color: var(--search-bar-gray) !important;
  border-radius: 6px 0 0 6px !important;
  padding-left: 8px;
}

.van-field__control {
  color: var(--text-main) !important;
}

.van-field__clear {
  color: var(--text-secondary) !important;
  font-size: 16px;
  padding: 4px;
}

.editor-container { 
  background-color: var(--card-bg);
  padding: 10px;
  overflow-y: auto;
  max-height: 80vh; 
}

.cropper-stage { 
  height: 50vh; 
  max-height: 500px;
  min-height: 300px;
  width: 100%;
  background: var(--cropper-stage-bg);
  position: relative; 
  border-radius: 8px;
  overflow: hidden;
}

.cropper-box {
  position: absolute; 
  top: 20px;
  bottom: 20px;
  left: 20px;
  right: 20px;
  background: transparent;
  font-size: 0;
}

.cropper-container { width: 100% !important; height: 100% !important; }

.cropper-canvas img, .cropper-view-box img { 
  max-width: none !important; 
  max-height: none !important; 
  filter: brightness(var(--b, 1)) contrast(var(--c, 1)); 
  transition: filter 0.1s; 
}

.cropper-bg { background-image: none !important; }

.controls-area { margin-top: 15px; padding: 0 10px; }
.control-row { display: flex; align-items: center; margin-bottom: 12px; gap: 10px; font-size: 14px; color: var(--text-main); }

.van-theme-dark .van-dialog {
  background-color: var(--card-bg) !important;
}

.van-theme-dark .van-dialog__header {
  color: var(--text-header) !important;
}

.van-theme-dark .van-dialog .van-button--default {
  background-color: transparent !important;
  color: var(--text-main) !important;
  border: 1px solid var(--border-color) !important;
}
</style>

<style scoped>
.theme-switch {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 50px;
  height: 50px;
  background: var(--card-bg);
  border-radius: 50%;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2000;
  font-size: 24px;
  border: 1px solid var(--border-color);
  transition: all 0.3s;
}
.theme-switch:hover {
  transform: scale(1.1);
}

.custom-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background-color: var(--header-bg);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color);
  transition: background 0.3s;
  gap: 10px;
  position: relative;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0; 
}

.header-logo {
  font-size: 28px;
}

.header-title {
  font-size: 22px;
  font-weight: 900;
  margin-left: 8px;
  background: linear-gradient(135deg, #00AEEC 0%, #a18cd1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: 1px;
  font-family: 'PingFang SC', 'Helvetica Neue', Arial, sans-serif;
}

.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  max-width: 600px; 
  gap: 12px;
}

.search-group {
  display: flex;
  align-items: center;
  flex: 1;
  position: relative;
  min-width: 0;
}

.header-search {
  flex: 1;
  padding: 0; 
}

.theme-btn-inline {
  display: flex;
  align-items: center;
  justify-content: center;
  width: auto;    
  height: 36px;     
  padding: 0 12px; 
  cursor: pointer;
  border-radius: 18px; 
  transition: background-color 0.2s;
  margin-right: 4px;
  background-color: var(--search-bar-gray); 
}

.theme-content {
  font-size: 13px; 
  font-weight: 500;
  white-space: nowrap; 
}

.theme-btn-inline:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.van-theme-dark .theme-btn-inline:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.search-btn {
  height: 34px;
  border-radius: 0 6px 6px 0;
  border: none;
  background-color: #00AEEC;
  border-color: #00AEEC;
  min-width: 44px;
}

.search-clear {
  position: absolute;
  right: 50px; 
  top: 50%;
  transform: translateY(-50%);
  color: #999;
  cursor: pointer;
  z-index: 10;
  padding: 4px;
  background: transparent;
  display: flex;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.action-btn {
  height: 32px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-btn {
  background-color: #00AEEC;
  border-color: #00AEEC;
}

.logout-btn {
  background-color: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.login-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--login-gradient); 
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  overflow: hidden;
}

.login-card {
  position: relative;
  width: 90%;
  max-width: 400px;
  box-sizing: border-box; 
  background: var(--card-bg); 
  backdrop-filter: blur(10px);
  border-radius: 8px;
  box-shadow: var(--card-shadow); 
  padding: 40px 30px;
  border-top: 4px solid #00AEEC;
  transition: background 0.3s, box-shadow 0.3s;
  margin: 0 auto; 
}

.login-theme-switch {
  position: absolute;
  top: 20px; 
  right: 20px;
  width: auto;    
  height: 32px;     
  padding: 0 12px;  
  background-color: var(--search-bar-gray); 
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  font-size: 13px; 
  font-weight: 500;
  transition: all 0.2s;
}

.login-theme-switch:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.van-theme-dark .login-theme-switch:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
  display: flex;
  flex-direction: column;
  align-items: center; 
}

.login-header h3 {
  margin: 0;
  font-size: 20px;
  color: var(--text-main); 
  font-weight: 500;
}

.login-logo {
  font-size: 48px;
  margin-bottom: 10px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-5px); }
  100% { transform: translateY(0px); }
}

.auth-form {
  padding-top: 25px;
}

.form-item {
  border: 1px solid var(--border-color); 
  border-radius: 4px;
  margin-bottom: 15px;
  overflow: hidden;
  transition: all 0.3s;
}

.form-item:focus-within {
  border-color: #00AEEC;
  box-shadow: 0 0 0 2px rgba(0, 174, 236, 0.2);
}

.custom-input {
  background: transparent; 
  padding: 10px 15px;
}
.input-icon {
  color: var(--input-icon-color);
}

.btn-area {
  margin-top: 25px;
}

.auth-options {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
  font-size: 13px;
  color: #00AEEC;
  cursor: pointer;
}

.main-content { 
  padding-bottom: 50px; 
  background-color: var(--app-bg); 
  min-height: 100vh; 
  transition: background-color 0.3s;
}

.action-panel { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; margin-top: 10px; }
.upload-tip { font-size: 12px; color: var(--text-secondary); }

.masonry-layout { column-count: 5; column-gap: 16px; padding: 0 16px; width: 100%; box-sizing: border-box; }

.pin-card { 
  break-inside: avoid; 
  margin-bottom: 16px; 
  border-radius: 16px; 
  overflow: hidden; 
  cursor: zoom-in; 
  transition: transform 0.2s ease, background 0.3s;
  background-color: var(--pin-card-bg); 
  border: 1px solid var(--border-color); 
}
.pin-card:hover { transform: translateY(-2px); }

.pin-image-wrapper { 
  position: relative; 
  width: 100%; 
  overflow: hidden; 
  background-color: #333; 
  min-height: 100px; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
}
.pin-image-wrapper img { width: 100%; height: auto; display: block; min-height: 100px; object-fit: cover; }

.pin-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); opacity: 0; transition: opacity 0.2s; display: flex; justify-content: flex-end; padding: 10px; gap: 8px; z-index: 10; box-sizing: border-box;}
.pin-card:hover .pin-overlay { opacity: 1; }

.pin-btn { width: 32px; height: 32px; border-radius: 50%; border: none; display: flex; align-items: center; justify-content: center; cursor: pointer; background: rgba(255, 255, 255, 0.9); color: #333; transition: transform 0.1s; position: relative; z-index: 20; }
.pin-btn:hover { transform: scale(1.1); background: white; }
.pin-btn.del:hover { color: red; }

.pin-info { padding: 8px 6px; }

.pin-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }
.tag-pill { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
.tag-pill.ai { 
  background-color: var(--tag-ai-bg); 
  color: var(--tag-ai-text); 
}
.tag-pill.user { 
  background-color: var(--tag-user-bg); 
  color: #00AEEC; 
  display: inline-flex; align-items: center; 
}
.tag-close { margin-left: 4px; font-size: 10px; cursor: pointer; }
.tag-add-btn { font-size: 14px; color: var(--text-secondary); cursor: pointer; padding: 0 4px; line-height: 20px; }

.pin-detail-list {
  display: flex;
  flex-direction: column;
  gap: 6px; 
  margin-top: 8px;
  padding-top: 4px;
}

.detail-row {
  display: flex;
  align-items: flex-start; 
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.detail-row .van-icon {
  width: 16px; 
  text-align: center; 
  margin-right: 4px; 
  margin-top: 1px; 
  flex-shrink: 0; 
}

.detail-row span {
  flex: 1;
  word-break: break-all; 
}

@media (max-width: 500px) {
  .custom-header {
    height: auto !important;
    flex-direction: column !important;
    padding: 0 !important;
    border-bottom: none !important;
  }

  .header-left {
    width: 100%;
    justify-content: center;
    padding: 12px 0;
    border-bottom: 1px solid var(--border-color);
  }
  
  .header-title {
    margin-left: 0;
    font-size: 18px;
  }

  .header-right {
    width: 100%;
    max-width: none;
    padding: 12px;
    box-sizing: border-box;
    display: grid !important;
    grid-template-columns: auto 1fr;
    gap: 12px;
    grid-template-areas: 
      "theme actions"
      "search search";
  }

  .theme-btn-inline {
    grid-area: theme; 
    width: auto;
    height: 36px;
    padding: 0 10px;
    background-color: var(--search-bar-gray);
    border-radius: 18px;
    margin: 0 !important;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .search-group {
    grid-area: search;
    width: 100%;
    margin: 0 !important;
  }
  
  .header-search {
    padding-left: 0;
  }

  .header-actions {
    grid-area: actions;
    display: flex !important;
    width: 100%;
    gap: 10px;
    align-items: center;
  }

  .header-uploader, 
  .logout-btn {
    flex: 1 1 0% !important; 
    width: 0 !important;
    min-width: 0 !important;
  }

  :deep(.van-uploader__wrapper),
  :deep(.van-uploader__input-wrapper) {
    width: 100% !important;
    display: flex !important;
  }

  .action-btn {
    width: 100% !important; 
    height: 36px;
    padding: 0;
    border-radius: 6px;
    font-size: 13px;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  
  :deep(.van-button__content) {
    width: 100%;
  }

  .btn-text {
    display: inline-block !important;
  }
}

@media (max-width: 1200px) { .masonry-layout { column-count: 4; } }
@media (max-width: 900px) { .masonry-layout { column-count: 3; } }
@media (max-width: 600px) { 
  .masonry-layout { column-count: 2; column-gap: 10px; padding: 0 10px; }
  .pin-overlay { opacity: 1; background: transparent; align-items: flex-start; } 
  .pin-btn { background: rgba(0,0,0,0.5); color: white; width: 28px; height: 28px; }
  .pin-info { padding: 6px 2px; }
}

.nav-btn { position: fixed; top: 50%; transform: translateY(-50%); width: 56px; height: 56px; background-color: rgba(30, 30, 30, 0.4); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 32px; cursor: pointer; transition: all 0.2s; z-index: 9999; backdrop-filter: blur(4px); border: 1px solid rgba(255,255,255,0.1); user-select: none; }
.nav-btn:hover { background-color: rgba(255, 255, 255, 0.2); transform: translateY(-50%) scale(1.1); }
.nav-btn.left { left: 40px; }
.nav-btn.right { right: 40px; }
.zoom-tip { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); color: rgba(255, 255, 255, 0.7); background: rgba(0, 0, 0, 0.5); padding: 5px 15px; border-radius: 20px; font-size: 12px; pointer-events: none; z-index: 9999; }
</style>