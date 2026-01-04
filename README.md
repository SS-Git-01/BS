# 图片管理网站

项目的结构如下所示：
```
BS/
├── backend/                    # 后端工程 (Flask + PyTorch)
│   ├── models/                 # 离线 AI 模型 (Chinese-CLIP, ResNet)
│   ├── ai_classify.py          # 图像分类功能实现
│   ├── app.py                  # Flask 应用主入口
│   ├── Dockerfile              # 后端镜像构建文件
│   ├── imagenet_labels.json    # 分类标签映射表
│   ├── llm_search.py           # 语义搜图功能实现
│   ├── mcp_server.py           # MCP 智能体服务端脚本
│   ├── raw_labels.js           # 标签处理工具
│   └── requirements.txt        # Python 依赖列表
│
├── database/
│   └── init.sql                # MySQL 数据库初始化脚本
│
├── frontend/                   # 前端工程 (Vue 3 + Vite)
│   ├── public/                 # 静态资源
│   ├── src/                    # 前端源代码
│   │   ├── router/             # 路由配置
│   │   ├── App.vue             # 根组件
│   │   └── main.js             # 前端入口文件
│   ├── index.html              # 页面入口
│   ├── package.json            # npm 依赖配置
│   └── vite.config.js          # Vite 构建配置
│
├── docker-compose.yml          # Docker 一键启动配置
└── README.md                   # 项目说明文档
```

> **注意**：本压缩包已包含 ResNet-50 和 Chinese-CLIP 的**本地模型权重**，启动时无需联网下载大文件，可直接离线运行。

## 1. 环境要求 

**Docker Desktop** (请确保已启动)
端口占用检查：确保本地 `5173` (前端), `5000` (后端), `3306` (数据库) 端口未被占用。

## 2. 启动步骤 

**解压**
解压压缩包，进入项目根目录。

**启动服务**
运行以下命令构建并启动容器：

```bash
docker-compose up --build
```
**注意：首次启动时下载各种python库等需要很长的时间，且下载完后，前端、后端的首次启动可能也需要几分钟，请耐心等待。**
后续再次启动只需输入：
```bash
docker-compose up 
```

**浏览器访问**
推荐使用Google Chrome浏览器。
PC端输入 `localhost:5173` 即可访问，也可将 `localhost` 替换为本机的IP地址。
手机端需和运行代码的PC连接同一WiFi，在PC的PowerShell中输入 `ipconfig` 查看IP地址，在手机浏览器中输入 `IP地址:5173` 访问。

**MCP接口使用**
推荐使用Cursor。
启动Cursor，点击右上角的设置符号，选择 `Tools & MCP` ，添加新的MCP接口，`mcp.json` 配置如下所示：
```json
{
  "mcpServers": {
    "cloud-album": {
      "command": "D:\\anaconda\\python.exe", 
      "args": [
        "E:\\BS\\backend\\mcp_server.py"
      ]
    }
  }
}
```
请将command和args中两个路径替换为本机中的python.exe和mcp_server.py的路径。
在使用MCP接口前，需要确保本机已经安装了mcp和httpx两个库，如果没有，请运行：
```bash
pip install mcp httpx
```
除此之外，请将 `mcp_server.py` 中的：
```python
USERNAME = "" #请在""内输入账号
PASSWORD = "" #请在""内输入密码
```
替换成已经成功注册的账号密码（请先在网页注册账号）。
现在可以在Cursor中让Agent登录图片管理网站，查找想要的图片。

**停止服务**
在终端输入：
```bash
docker-compose down
```
即可停止服务。

## 3. 注意

使用手机浏览器访问网站时，请确保手机和电脑连接的是同一WiFi，先查看电脑的IP地址再从手机端访问网站。
由于手机浏览器的隐私保护机制，从手机浏览器上传图片可能会将拍摄地点和拍摄设备信息抹去，推荐将照片先上传到电脑上，使用电脑浏览器上传。