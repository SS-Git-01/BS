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
        <van-search 
          v-model="searchQuery" 
          show-action 
          placeholder="🔍 搜地点 / 标签 (如: 生日, mask)" 
          @search="onSearch"
          @clear="onSearch"
        >
          <template #action>
            <div @click="onSearch">搜索</div>
          </template>
        </van-search>
      </van-sticky>

      <van-cell-group inset title="上传新照片" style="margin-top: 10px;">
        <div class="upload-box">
          <van-uploader :after-read="afterRead" v-model="fileList" :max-count="1" upload-text="点击上传" />
          <p class="tip-text">支持自动提取拍摄时间与地点 (Exif)</p>
        </div>
      </van-cell-group>

      <van-divider>我的照片库 ({{ images.length }} 张)</van-divider>
      <van-empty v-if="images.length === 0" description="没有找到照片哦~" />

      <van-grid :column-num="2" gutter="10" class="image-grid">
        <van-grid-item v-for="(img, index) in images" :key="img.id" class="grid-item-wrapper">
          <van-image
            class="hover-scale-img grid-thumb"
            :src="getImageUrl(img.thumbnail)" 
            height="150" 
            fit="contain"
            @click="openPreview(index)" 
          />
          
          <div class="action-btns">
            <div class="circle-btn edit" @click.stop="openEditor(img)">
              <van-icon name="edit" />
            </div>
            <div class="circle-btn del" @click.stop="confirmDelete(img)">
              <van-icon name="delete-o" />
            </div>
          </div>

          <div class="image-info">
            <div class="info-row">📅 {{ formatDate(img.capture_date) }}</div>
            <div class="info-row" v-if="img.resolution && img.resolution !== '未知'">📐 {{ img.resolution }}</div>
            <div class="info-row" v-if="img.device && img.device !== 'Unknown'">📱 {{ img.device }}</div>
            <div class="info-row" v-if="img.location && img.location !== 'Unknown'">📍 {{ img.location }}</div>
            
            <div class="tags-row">
              <van-tag 
                v-for="(tag, tIndex) in img.tags" 
                :key="'u'+tIndex" 
                class="user-tag" 
                closeable 
                size="medium"
                type="primary"
                plain
                @close.stop="handleRemoveTag(img, tag)"
              >
                {{ tag }}
              </van-tag>
              
              <span v-for="(tag, tIndex) in (img.ai_tags || []).slice(0, 3)" :key="'a'+tIndex" class="ai-tag">
                🤖 {{ tag.label }}
              </span>
              <van-icon name="add-o" class="add-tag-btn" @click.stop="openAddTagDialog(img)" />
            </div>
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
              <van-button size="small" icon="replay" @click="rotateImage">90°</van-button>
            </div>
            
            <div class="control-row">
              <span>亮度:</span>
              <van-slider v-model="editParams.brightness" :min="0.5" :max="1.5" :step="0.1" style="width: 70%" />
            </div>

            <div class="control-row">
              <span>对比:</span>
              <van-slider v-model="editParams.contrast" :min="0.5" :max="1.5" :step="0.1" style="width: 70%" />
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
  });
};
const resetZoom = () => {
  currentZoom.value = 1;
  const allImages = document.querySelectorAll('.van-image-preview__image');
  allImages.forEach(img => { img.style.transform = ''; img.style.transition = 'transform 0.3s ease-out'; });
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

const fetchImages = async () => {
  if (!token.value) return;
  try {
    const res = await axios.get(`${API_BASE}/images`, { 
      params: { q: searchQuery.value }, 
      headers: { 'Authorization': `Bearer ${token.value}` } 
    });
    images.value = res.data;
  } catch (err) { if (err.response && err.response.status === 401) logout(); }
};

const onSearch = () => {
  fetchImages(); 
};

const confirmDelete = (img) => {
  showConfirmDialog({ title: '确认删除', message: '删除后无法恢复，确定要删除这张照片吗？' })
    .then(async () => {
      try {
        await axios.delete(`${API_BASE}/images/${img.id}`, { headers: { 'Authorization': `Bearer ${token.value}` } });
        showSuccessToast('删除成功');
        fetchImages();
      } catch (err) { showFailToast('删除失败'); }
    }).catch(() => {});
};

const afterRead = async (file) => {
  file.status = 'uploading';
  const formData = new FormData();
  formData.append('file', file.file);
  try {
    await axios.post(`${API_BASE}/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data', 'Authorization': `Bearer ${token.value}` } });
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
    const targetImage = images.value.find(img => img.id === currentEditingImage.value.id);
    
    if (targetImage) {
      targetImage.thumbnail = targetImage.thumbnail.split('?')[0] + `?t=${timestamp}`;
      targetImage.filename = targetImage.filename.split('?')[0] + `?t=${timestamp}`;
      if (res.data.resolution) {
        targetImage.resolution = res.data.resolution;
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
.grid-item-wrapper { position: relative; }

/* 缩略图样式优化：添加背景色以配合 contain 模式 */
.grid-thumb {
  background-color: #ebedf0;
}

.action-btns { position: absolute; top: 5px; right: 5px; display: flex; gap: 8px; z-index: 10; }
.circle-btn { width: 24px; height: 24px; border-radius: 4px; color: #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; }
.circle-btn.del { background: rgba(0, 0, 0, 0.5); }
.circle-btn.del:hover { background: rgba(255, 0, 0, 0.8); }
.circle-btn.edit { background: rgba(0, 0, 0, 0.5); }
.circle-btn.edit:hover { background: rgba(25, 137, 250, 0.8); }

.nav-btn { position: fixed; top: 50%; transform: translateY(-50%); width: 56px; height: 56px; background-color: rgba(30, 30, 30, 0.4); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 32px; cursor: pointer; transition: all 0.2s; z-index: 9999; backdrop-filter: blur(4px); border: 1px solid rgba(255,255,255,0.1); user-select: none; }
.nav-btn:hover { background-color: rgba(255, 255, 255, 0.2); transform: translateY(-50%) scale(1.1); }
.nav-btn.left { left: 40px; }
.nav-btn.right { right: 40px; }
.zoom-tip { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); color: rgba(255, 255, 255, 0.7); background: rgba(0, 0, 0, 0.5); padding: 5px 15px; border-radius: 20px; font-size: 12px; pointer-events: none; z-index: 9999; }
@media (hover: hover) and (pointer: fine) { .hover-scale-img >>> .van-image__img { transition: transform 0.3s ease; } .hover-scale-img:hover >>> .van-image__img { transform: scale(1.1); } }
.tags-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; align-items: center; }
.ai-tag { font-size: 10px; background-color: #f0f9eb; color: #67c23a; padding: 1px 4px; border-radius: 4px; border: 1px solid #e1f3d8; display: inline-block; }
.user-tag { font-size: 10px; margin-right: 4px; margin-bottom: 4px; }
.add-tag-btn { color: #1989fa; font-size: 14px; cursor: pointer; padding: 2px; }
</style>

<style>
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

.cropper-box > img {
  max-width: 100%;
  display: block;
}

.controls-area { 
  margin-top: 15px; 
  padding: 0 10px; 
}

.control-row { 
  display: flex; 
  align-items: center; 
  margin-bottom: 12px; 
  gap: 10px; 
  font-size: 14px; 
  color: #333; 
}

.cropper-container {
  width: 100% !important;
  height: 100% !important;
}

.cropper-canvas img,
.cropper-view-box img {
  max-width: none !important;
  max-height: none !important;
  filter: brightness(var(--b, 1)) contrast(var(--c, 1));
  transition: filter 0.1s;
}

.cropper-bg {
  background-image: none !important;
}
</style>