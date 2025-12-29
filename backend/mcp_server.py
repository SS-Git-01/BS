import httpx
from mcp.server.fastmcp import FastMCP
import asyncio

mcp = FastMCP("CloudAlbum")

API_BASE = "http://localhost:5000/api"

USERNAME = "test"
PASSWORD = "123456"

_cached_token = None

async def get_token():
    global _cached_token
    if _cached_token:
        return _cached_token
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{API_BASE}/auth/login", json={
                "username": USERNAME,
                "password": PASSWORD
            })
            if resp.status_code == 200:
                data = resp.json()
                _cached_token = data.get("token")
                return _cached_token
        except:
            pass
    return None

async def get_headers():
    token = await get_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

@mcp.tool()
async def search_photos(query: str, limit: int = 5) -> str:
    url = f"{API_BASE}/images"
    params = {"q": query, "limit": limit}
    
    headers = await get_headers()
    if not headers:
        return "错误：登录失败，请检查脚本中的用户名和密码。"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            
            if resp.status_code == 401:
                global _cached_token
                _cached_token = None
                return "错误：Token 过期，请重试。"
                
            if resp.status_code != 200:
                return f"API 错误: {resp.status_code}"
            
            data = resp.json()
            items = data.get("items", [])
            
            if not items:
                return "未找到匹配的照片。"
            
            result = f"🔍 找到了 {len(items)} 张照片：\n"
            for img in items:
                img_url = f"http://localhost:5000/uploads/thumb_{img['filename']}"
                result += f"![照片预览]({img_url})\n"
                result += f"- [ID:{img['id']}] {img['filename']}\n"
                result += f"  📅 时间: {img['capture_date']}\n"
                result += f"  📍 地点: {img['location']}\n"
                ai_tags = [t['label'] for t in img.get('ai_tags', [])]
                result += f"  🏷️ 标签: {', '.join(ai_tags[:5])}\n"
                result += "---\n"
            return result
            
        except Exception as e:
            return f"请求失败: {str(e)}"

if __name__ == "__main__":
    mcp.run()