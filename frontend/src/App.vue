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
      
      <van-sticky :offset-top="46">
        <div class="search-bar-container">
          <van-search 
            v-model="searchQuery" 
            show-action 
            shape="round"
            background="transparent"
            placeholder="🔍 搜地点 / 标签 (如: 生日, mask)" 
            @search="onSearch"
            @clear="onSearch"
          >
            <template #action>
              <div @click="onSearch" class="search-btn">搜索</div>
            </template>
          </van-search>
        </div>
      </van-sticky>

      <div class="action-panel">
         <van-uploader 
            :after-read="afterRead" 
            v-model="fileList" 
            multiple 
            :max-count="9" 
            accept="image/*"
          >
           <van-button icon="plus" type="primary" round size="small">上传照片</van-button>
         </van-uploader>
         <span class="upload-tip">支持 Exif 自动识别</span>
      </div>

      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
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
              
              <div class="pin-meta">
                <div class="meta-row location" v-if="img.location && img.location !== 'Unknown'">
                  <van-icon name="location-o" /> {{ img.location }}
                </div>
                <div class="meta-row date">
                   📅 {{ formatDate(img.capture_date).split(' ')[0] }}
                </div>
              </div>

              <div class="pin-tech-info">
                <span v-if="img.resolution && img.resolution !== '未知'" class="tech-item">
                  <van-icon name="photo-o" /> {{ img.resolution }}
                </span>
                <span v-if="img.device && img.device !== 'Unknown'" class="tech-item">
                  <van-icon name="desktop-o" /> {{ img.device }}
                </span>
              </div>

            </div>

          </div>
        </div>
      </van-list>

      <div style="margin: 30px 20px;">
        <van-button color="#efefef" block round @click="logout" style="color: #333; font-weight: bold;">退出登录</van-button>
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

      <van-dialog 
        v-model:show="showAddTagDialog" 
        title="添加标签" 
        show-cancel-button
        @confirm="submitAddTag"
      >
        <van-cell-group inset style="margin: 20px 0;">
          <van-field
            v-model="newTagName"
            placeholder="请输入标签名（如：生日、旅游）"
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
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import axios from 'axios';
import { showToast, showSuccessToast, showFailToast, showConfirmDialog } from 'vant';

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
const previewImages = computed(() => images.value.map(img => IMG_BASE + img.filename));

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
    setTimeout(() => {
        resetZoom();
    }, 50);
  });
};
const resetZoom = () => {
  currentZoom.value = 1;
  const allImages = document.querySelectorAll('.van-image-preview__image');
  allImages.forEach(img => {
      img.style.transform = 'scale(1) translate(0, 0)';
      img.style.transition = 'transform 0.3s ease-out';
  });
};
const onChange = (newIndex) => { previewIndex.value = newIndex; resetZoom(); };
const prevImage = () => { if (previewRef.value) { const newIndex = (previewIndex.value - 1 + images.value.length) % images.value.length; previewRef.value.swipeTo(newIndex); } };
const nextImage = () => { if (previewRef.value) { const newIndex = (previewIndex.value + 1) % images.value.length; previewRef.value.swipeTo(newIndex); } };
const handleKeyDown = (e) => { if (!showPreview.value) return; switch (e.key) { case 'Escape': showPreview.value = false; break; case 'ArrowLeft': prevImage(); break; case 'ArrowRight': nextImage(); break; } };
const handleWheel = (e) => {
  if (!showPreview.value) return;
  e.preventDefault();
  const ZOOM_SPEED = 0.001; 
  let newZoom = currentZoom.value - e.deltaY * ZOOM_SPEED;
  if (newZoom < 0.5) newZoom = 0.5; if (newZoom > 5) newZoom = 5;
  currentZoom.value = newZoom;
  const allImages = document.querySelectorAll('.van-image-preview__swipe .van-image-preview__image');
  const currentImg = allImages[previewIndex.value];
  if (currentImg) { currentImg.style.transition = 'none'; currentImg.style.transform = `scale(${newZoom})`; }
};
watch(showPreview, (val) => { if (!val) { window.removeEventListener('keydown', handleKeyDown); window.removeEventListener('wheel', handleWheel); } });

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
    
    const newImageId = res.data.id;
    
    if (newImageId) {
      pollImageStatus(newImageId);
    }
    
  } catch (err) {
    item.status = 'failed';
    item.message = '失败';
    showFailToast('部分图片上传失败');
  }
};

const afterRead = async (items) => {
  const files = Array.isArray(items) ? items : [items];
  await Promise.all(files.map(file => uploadOneFile(file)));
  setTimeout(() => {
    fileList.value = fileList.value.filter(item => item.status === 'failed');
    if (fileList.value.length === 0) {
      showSuccessToast('所有上传完成');
      resetList(); 
    }
  }, 1000);
};

const onLogin = async (values) => {
  try {
    const res = await axios.post(`${API_BASE}/auth/login`, values);
    token.value = res.data.token;
    localStorage.setItem('token', res.data.token);
    showSuccessToast('登录成功');
    resetList(); 
  } catch (err) { showFailToast(err.response?.data?.message || '登录失败'); }
};

const onRegister = async (values) => { try { await axios.post(`${API_BASE}/auth/register`, values); showSuccessToast('注册成功'); activeTab.value = 0; } catch (err) { showFailToast('注册失败'); } };

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
    await axios.put(`${API_BASE}/images/${currentEditingImage.value.id}/edit`, {
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

<style scoped>
.auth-container { padding: 40px 20px; text-align: center; }
.logo-area { margin-bottom: 40px; }
.logo-area h1 { font-size: 60px; margin: 0; }
.main-content { padding-bottom: 50px; background-color: #ffffff; min-height: 100vh; }

.search-bar-container { padding: 10px 16px; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }
.search-btn { font-weight: bold; color: #333; }

.action-panel { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; }
.upload-tip { font-size: 12px; color: #999; }

/* 瀑布流 Masonry 布局核心 */
.masonry-layout {
  column-count: 5;
  column-gap: 16px;
  padding: 0 16px;
  width: 100%;
  box-sizing: border-box;
}

.pin-card {
  break-inside: avoid;
  margin-bottom: 16px;
  border-radius: 16px;
  overflow: hidden;
  cursor: zoom-in;
  /* 移除阴影或使用极淡阴影，保持干净 */
  transition: transform 0.2s ease;
}

.pin-card:hover {
  transform: translateY(-2px);
}

.pin-image-wrapper {
  position: relative;
  width: 100%;
  border-radius: 16px;
  overflow: hidden;
  background-color: #f5f5f5; /* 占位色 */
}

.pin-image-wrapper img {
  width: 100%;
  height: auto;
  display: block; /* 消除底部空隙 */
}

/* 遮罩层与按钮 */
.pin-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.2);
  opacity: 0;
  transition: opacity 0.2s;
  display: flex;
  justify-content: flex-end;
  padding: 10px;
  gap: 8px;
}

.pin-card:hover .pin-overlay {
  opacity: 1;
}

.pin-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  transition: transform 0.1s;
}

.pin-btn:hover {
  transform: scale(1.1);
  background: white;
}
.pin-btn.del:hover { color: red; }

/* 信息区域 */
.pin-info {
  padding: 8px 4px;
}

.pin-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 4px;
}

.tag-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.tag-pill.ai {
  background-color: #f0f0f0;
  color: #111;
}

.tag-pill.user {
  background-color: #e6f7ff;
  color: #1890ff;
  display: inline-flex;
  align-items: center;
}

.tag-close { margin-left: 4px; font-size: 10px; cursor: pointer; }

.tag-add-btn {
  font-size: 14px;
  color: #999;
  cursor: pointer;
  padding: 0 4px;
  line-height: 20px;
}

.pin-meta {
  display: flex;
  flex-direction: column; /* 关键：改为垂直堆叠 */
  align-items: flex-start; /* 左对齐 */
  gap: 6px; /* 地点和日期之间的间距 */
  font-size: 11px;
  color: #888;
  margin-top: 8px;
}

.meta-row { display: flex; align-items: center; gap: 2px; }

.meta-row.location {
  white-space: normal; /* 允许换行 */
  overflow: visible;   /* 显示全部内容 */
  text-overflow: clip; /* 去掉省略号 */
  max-width: 100%;     /* 占满宽度 */
  line-height: 1.4;    /* 增加行高，多行时更好看 */
  word-break: break-all; /* 防止纯英文地址不换行 */
}

/* 新增：技术参数行 (分辨率、设备) */
.pin-tech-info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px dashed #eee; /* 加条虚线分隔，更清晰 */
  font-size: 10px;
  color: #999;
}

.tech-item {
  display: flex;
  align-items: center;
  gap: 2px;
  background-color: #f9f9f9;
  padding: 1px 4px;
  border-radius: 4px;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .masonry-layout { column-count: 4; }
}

@media (max-width: 900px) {
  .masonry-layout { column-count: 3; }
}

@media (max-width: 600px) {
  .masonry-layout { column-count: 2; column-gap: 10px; padding: 0 10px; }
  .pin-overlay { opacity: 1; background: transparent; align-items: flex-start; } 
  .pin-btn { background: rgba(0,0,0,0.5); color: white; width: 28px; height: 28px; }
  .pin-info { padding: 6px 2px; }
}

/* 预览与编辑相关样式保持不变 */
.nav-btn { position: fixed; top: 50%; transform: translateY(-50%); width: 56px; height: 56px; background-color: rgba(30, 30, 30, 0.4); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 32px; cursor: pointer; transition: all 0.2s; z-index: 9999; backdrop-filter: blur(4px); border: 1px solid rgba(255,255,255,0.1); user-select: none; }
.nav-btn:hover { background-color: rgba(255, 255, 255, 0.2); transform: translateY(-50%) scale(1.1); }
.nav-btn.left { left: 40px; }
.nav-btn.right { right: 40px; }
.zoom-tip { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); color: rgba(255, 255, 255, 0.7); background: rgba(0, 0, 0, 0.5); padding: 5px 15px; border-radius: 20px; font-size: 12px; pointer-events: none; z-index: 9999; }
</style>

<style>
/* Cropper Global Styles */
.editor-container { 
  background-color: #fff;
  padding: 10px;
  overflow-y: auto;
  max-height: 80vh; 
}
.cropper-stage { 
  height: 50vh; 
  max-height: 500px;
  min-height: 300px;
  width: 100%;
  background: #ebedf0;
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
.van-image-preview__image {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain !important;
  max-width: none !important;
  max-height: none !important;
  margin: 0 !important;
}

.van-image-preview__swipe-item {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  overflow: hidden !important;
}

.cropper-box > img { max-width: 100%; display: block; }
.controls-area { margin-top: 15px; padding: 0 10px; }
.control-row { display: flex; align-items: center; margin-bottom: 12px; gap: 10px; font-size: 14px; color: #333; }
.cropper-container { width: 100% !important; height: 100% !important; }
.cropper-canvas img, .cropper-view-box img { max-width: none !important; max-height: none !important; filter: brightness(var(--b, 1)) contrast(var(--c, 1)); transition: filter 0.1s; }
.cropper-bg { background-image: none !important; }
</style>