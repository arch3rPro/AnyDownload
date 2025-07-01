import yaml
import os
import time
import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from f2.apps.douyin.handler import DouyinHandler
from f2.apps.douyin.utils import SecUserIdFetcher, AwemeIdFetcher
from urllib.parse import unquote, urlparse, quote

app = FastAPI()

# 添加CORS中间件，允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 新增：主页链接校验函数
def is_valid_douyin_user_url(url: str) -> bool:
    return url.startswith("https://www.douyin.com/user/") or url.startswith("https://v.douyin.com/")

def get_latest_config():
    with open("/app/app.yaml", "r", encoding="utf-8") as f:
        config_all = yaml.safe_load(f)
    return config_all.get("douyin", {})

@app.get("/douyin/user_post")
async def download_user_post(
    url: str = Query(..., description="抖音用户主页url"),
    mode: str = Query("post", description="下载模式"),
    min_cursor: int = Query(0, description="最小页码"),
    max_cursor: int = Query(0, description="最大页码"),
    page_counts: int = Query(20, description="每页数量"),
    max_counts: Optional[int] = Query(None, description="最大作品数"),
):
    """
    下载抖音用户发布的作品，支持伪实时回显下载进度
    """
    # 新增主页链接校验
    if not is_valid_douyin_user_url(url):
        def err_stream():
            yield "解析失败: 输入的URL不合法。类名：SecUserIdFetcher\n"
        return StreamingResponse(err_stream(), media_type="text/plain")
    kwargs = get_latest_config().copy()
    kwargs.update({
        "mode": mode,
        "path": kwargs.get("path", "Download"),
        "url": url,
    })
    if page_counts:
        kwargs["page_counts"] = page_counts
    if max_counts is not None:
        kwargs["max_counts"] = max_counts
    # 修复：确保naming有默认值
    if not kwargs.get("naming"):
        kwargs["naming"] = "{desc}_{aweme_id}"

    if "headers" not in kwargs or not isinstance(kwargs["headers"], dict):
        kwargs["headers"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Referer": "https://www.douyin.com/",
        }
    if "cookie" not in kwargs or not kwargs["cookie"]:
        def err_stream():
            yield "配置文件缺少cookie字段\n"
        return StreamingResponse(err_stream(), media_type="text/plain")

    handler = DouyinHandler(kwargs)

    async def event_stream():
        yield "开始采集作品信息...\n"
        sec_user_id = await SecUserIdFetcher.get_sec_user_id(url)
        video_count = 0
        video_descs = []
        async for post in handler.fetch_user_post_videos(
            sec_user_id=sec_user_id,
            min_cursor=min_cursor,
            max_cursor=max_cursor,
            page_counts=page_counts,
            max_counts=max_counts
        ):
            for item in post._to_list():
                video_count += 1
                video_descs.append(item.get('desc', '无标题'))
                yield f"采集到作品: {item.get('desc','无标题')} (aweme_id: {item.get('aweme_id')})\n"
        yield f"共采集到{video_count}个作品，开始触发下载...\n"

        # 触发下载
        await handler.handle_user_post()
        yield "下载任务已触发，开始监控Download目录...\n"

        # 监控Download目录下文件数量变化
        download_dir = os.path.join(
            kwargs.get("path", "Download"),
            "douyin",
            "post"
        )
        # 取第一个作品的desc作为子目录名（实际F2会用用户昵称，需根据实际情况调整）
        if video_descs:
            # 这里只是示例，实际应用F2的用户目录命名规则
            user_dirs = os.listdir(download_dir) if os.path.exists(download_dir) else []
            if user_dirs:
                user_dir = os.path.join(download_dir, user_dirs[0])
                last_count = 0
                for _ in range(60):  # 最多监控60次（约1分钟）
                    files = []
                    for root, dirs, fs in os.walk(user_dir):
                        for f in fs:
                            if f.endswith(".mp4"):
                                files.append(os.path.join(root, f))
                    if len(files) > last_count:
                        yield f"已下载视频数: {len(files)}\n"
                        last_count = len(files)
                    if len(files) >= video_count:
                        yield "全部视频已下载完成！\n"
                        break
                    time.sleep(2)
                else:
                    yield "下载未全部完成，请稍后手动检查Download目录。\n"
            else:
                yield "未找到用户下载目录，可能采集失败或无权限。\n"
        else:
            yield "未采集到任何作品，无法监控下载进度。\n"

    return StreamingResponse(event_stream(), media_type="text/plain")

@app.get("/douyin/one_video")
async def download_one_video(
    url: Optional[str] = Query(None, description="抖音作品链接"),
    aweme_id: Optional[str] = Query(None, description="抖音作品aweme_id"),
):
    """
    下载单个抖音作品，支持实时回显下载进度
    """
    kwargs = get_latest_config().copy()
    kwargs.update({
        "mode": "one",
        "path": kwargs.get("path", "Download"),
    })
    if "headers" not in kwargs or not isinstance(kwargs["headers"], dict):
        kwargs["headers"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Referer": "https://www.douyin.com/",
        }
    if "cookie" not in kwargs or not kwargs["cookie"]:
        def err_stream():
            yield "配置文件缺少cookie字段\n"
        return StreamingResponse(err_stream(), media_type="text/plain")

    handler = DouyinHandler(kwargs)

    async def event_stream():
        # 获取aweme_id
        real_aweme_id = aweme_id
        if not real_aweme_id and url:
            real_aweme_id = await AwemeIdFetcher.get_aweme_id(url)
        if not real_aweme_id:
            yield "缺少aweme_id或url参数，无法下载\n"
            return

        yield f"开始下载作品: {real_aweme_id}\n"
        try:
            # 需要将aweme_id放入kwargs["url"]，以便handle_one_video内部能正确获取
            kwargs["url"] = url if url else f"https://www.douyin.com/video/{real_aweme_id}"
            handler = DouyinHandler(kwargs)
            await handler.handle_one_video()
            yield "下载任务已触发，请到Download目录查看视频\n"
        except Exception as e:
            yield f"下载失败: {str(e)}\n"

    return StreamingResponse(event_stream(), media_type="text/plain")

@app.get("/douyin/parse_video")
async def parse_video(url: str = Query(..., description="抖音作品链接")):
    """
    解析抖音视频真实直链，不下载，直接返回mp4地址
    """
    kwargs = get_latest_config().copy()
    kwargs.update({
        "mode": "one",
        "url": url,
    })
    # 修复：确保headers和cookie有默认值
    if "headers" not in kwargs or not isinstance(kwargs["headers"], dict):
        kwargs["headers"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Referer": "https://www.douyin.com/",
        }
    if "cookie" not in kwargs or not kwargs["cookie"]:
        return JSONResponse(content={"code": 1, "msg": "配置文件缺少cookie字段"})
    handler = DouyinHandler(kwargs)
    try:
        aweme_id = await AwemeIdFetcher.get_aweme_id(url)
        video = await handler.fetch_one_video(aweme_id)
        play_addr = video.video_play_addr
        if isinstance(play_addr, list):
            real_url = play_addr[0] if play_addr else None
        else:
            real_url = play_addr
        if real_url:
            return JSONResponse(content={
                "code": 0,
                "msg": "ok",
                "data": {
                    "url": real_url,
                    "aweme_id": getattr(video, 'aweme_id', None),
                    "desc": getattr(video, 'desc', None) or ""
                }
            })
        else:
            return JSONResponse(content={"code": 1, "msg": "未获取到视频直链"})
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": f"解析失败: {str(e)}"})

@app.get("/douyin/proxy_download")
async def proxy_download(
    url: str = Query(..., description="抖音视频直链"),
    aweme_id: str = Query(None, description="抖音视频ID"),
    desc: str = Query(None, description="视频标题")
):
    """
    后端中转抖音视频直链，带必要请求头，防止403，并设置Content-Disposition文件名，支持中文
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Referer": "https://www.douyin.com/",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                # 优先desc，其次aweme_id，否则用url文件名
                filename = None
                if desc:
                    safe_desc = desc.strip().replace('/', '_').replace('\\', '_').replace('"', '').replace("'", '')
                    filename = f"{safe_desc}.mp4"
                elif aweme_id:
                    filename = f"{aweme_id}.mp4"
                else:
                    path = urlparse(url).path
                    filename = unquote(path.split('/')[-1]) or 'video.mp4'
                    if not filename.endswith('.mp4'):
                        filename = 'video.mp4'
                # 兼容中文/特殊字符文件名
                filename_ascii = filename.encode('utf-8', 'ignore').decode('ascii', 'ignore') or 'video.mp4'
                disposition = f"attachment; filename=\"{filename_ascii}\"; filename*=UTF-8''{quote(filename)}"
                print(f"proxy_download: desc={desc}, aweme_id={aweme_id}, filename={filename}, disposition={disposition}")
                return StreamingResponse(
                    resp.aiter_bytes(),
                    media_type="video/mp4",
                    headers={
                        "Content-Disposition": disposition
                    }
                )
            else:
                return JSONResponse(content={"code": 1, "msg": f"抖音CDN拒绝访问: {resp.status_code}"})
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": f"中转下载失败: {str(e)}"})

# 新增：批量解析主页作品直链接口
@app.get("/douyin/parse_user_posts")
async def parse_user_posts(
    url: str = Query(..., description="抖音用户主页url"),
    min_cursor: int = Query(0, description="最小页码"),
    max_cursor: int = Query(0, description="最大页码"),
    page_counts: int = Query(20, description="每页数量"),
    max_counts: Optional[int] = Query(None, description="最大作品数"),
):
    """
    批量解析抖音主页下所有作品的真实直链
    """
    if not is_valid_douyin_user_url(url):
        return JSONResponse(content={"code": 1, "msg": "请输入有效的抖音主页链接！"})

    kwargs = get_latest_config().copy()
    kwargs.update({
        "mode": "post",
        "path": kwargs.get("path", "Download"),
        "url": url,
    })
    if page_counts:
        kwargs["page_counts"] = page_counts
    if max_counts is not None:
        kwargs["max_counts"] = max_counts
    if not kwargs.get("naming"):
        kwargs["naming"] = "{desc}_{aweme_id}"

    if "headers" not in kwargs or not isinstance(kwargs["headers"], dict):
        kwargs["headers"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Referer": "https://www.douyin.com/",
        }
    if "cookie" not in kwargs or not kwargs["cookie"]:
        return JSONResponse(content={"code": 1, "msg": "配置文件缺少cookie字段"})

    handler = DouyinHandler(kwargs)
    try:
        sec_user_id = await SecUserIdFetcher.get_sec_user_id(url)
        result = []
        async for post in handler.fetch_user_post_videos(
            sec_user_id=sec_user_id,
            min_cursor=min_cursor,
            max_cursor=max_cursor,
            page_counts=page_counts,
            max_counts=max_counts
        ):
            for item in post._to_list():
                aweme_id = item.get('aweme_id')
                desc = item.get('desc', '')
                try:
                    video = await handler.fetch_one_video(aweme_id)
                    play_addr = video.video_play_addr
                    real_url = play_addr[0] if isinstance(play_addr, list) and play_addr else play_addr
                except Exception as e:
                    real_url = None
                result.append({
                    "aweme_id": aweme_id,
                    "desc": desc,
                    "url": real_url
                })
        return JSONResponse(content={"code": 0, "msg": "ok", "data": result})
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": f"解析失败: {str(e)}"})

@app.post("/douyin/set_cookie")
async def set_cookie(request: Request):
    """
    设置抖音cookie，写入配置文件
    """
    data = await request.json()
    cookie = data.get("cookie", "").strip()
    # 清理所有换行、回车、制表符和多余空格
    cookie = cookie.replace('\n', '').replace('\r', '').replace('\t', '').replace('  ', ' ')
    if not cookie:
        return {"code": 1, "msg": "Cookie不能为空"}
    import yaml
    config_path = "/app/app.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_all = yaml.safe_load(f)
        config_all.setdefault("douyin", {})["cookie"] = cookie
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_all, f, allow_unicode=True)
        return {"code": 0, "msg": "Cookie已保存"}
    except Exception as e:
        return {"code": 1, "msg": f"保存失败: {str(e)}"}

@app.get("/douyin/check_cookie")
async def check_cookie():
    """
    检查抖音cookie是否存在且有效
    code: 0=有效, 1=无cookie, 2=无效
    """
    import yaml
    import httpx
    config_path = "/app/app.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_all = yaml.safe_load(f)
        cookie = config_all.get("douyin", {}).get("cookie", "").strip()
        if not cookie:
            return {"code": 1, "msg": "未配置Cookie"}
        # 检查有效性：请求抖音主页，判断是否为已登录状态
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Cookie": cookie,
            "Referer": "https://www.douyin.com/",
        }
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.get("https://www.douyin.com/", headers=headers)
            # 简单判断：页面含有登录用户信息（如"登录/注册"不存在，或有"退出登录"等）
            if resp.status_code == 200:
                text = resp.text
                if ("登录/注册" not in text) and ("douyin.com/user/" in text or "退出登录" in text or "creatorCenter" in text):
                    return {"code": 0, "msg": "Cookie有效"}
                else:
                    return {"code": 2, "msg": "Cookie无效或已过期"}
            else:
                return {"code": 2, "msg": f"请求失败，状态码{resp.status_code}"}
    except Exception as e:
        return {"code": 1, "msg": f"检测失败: {str(e)}"}
