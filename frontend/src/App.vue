<template>
  <van-config-provider>
    <div style="padding: 20px;">
      <h2>图片管理系统登录</h2>
      
      <van-form @submit="onSubmit">
        <van-cell-group inset>
          <van-field
            v-model="username"
            name="username"
            label="用户名"
            placeholder="用户名"
            :rules="[{ required: true, message: '请填写用户名' }]"
          />
          <van-field
            v-model="password"
            type="password"
            name="password"
            label="密码"
            placeholder="密码"
            :rules="[{ required: true, message: '请填写密码' }]"
          />
        </van-cell-group>
        <div style="margin: 16px;">
          <van-button round block type="primary" native-type="submit">
            登录
          </van-button>
        </div>
      </van-form>

      <div v-if="token" style="margin-top:20px; word-break: break-all;">
        <p style="color: green;">登录成功！</p>
        <p>Token: {{ token }}</p>
      </div>
    </div>
  </van-config-provider>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';
// 引入 Vant 样式 (简单起见全局引入，实际项目推荐按需引入)
import 'vant/lib/index.css'; 

const username = ref('');
const password = ref('');
const token = ref('');

const onSubmit = async (values) => {
  try {
    // 发送请求给后端
    const res = await axios.post('http://localhost:5000/api/auth/login', {
      username: values.username,
      password: values.password
    });
    
    // 获取 Token 并显示
    token.value = res.data.token;
    localStorage.setItem('token', token.value); // 存入本地
    alert('登录成功: ' + res.data.username);
    
  } catch (error) {
    console.error(error);
    alert('登录失败: ' + (error.response?.data?.message || '未知错误'));
  }
};
</script>