# -*- coding:utf-8 -*-

import json
import time
import traceback

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

import schemas
from deps import get_token
from utils import generate_lyrics, generate_music, get_feed, get_lyrics, get_credits
from cookie import suno_auth, start_keep_alive

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get_root():
    return schemas.Response()


@app.post("/generate")
async def generate(
    data: schemas.CustomModeGenerateParam, token: str = Depends(get_token)
):
    try:
        resp = await generate_music(data.dict(), token)
        return resp
    except Exception as e:
        raise HTTPException(
            detail=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.post("/generate/description-mode")
async def generate_with_song_description(
    data: schemas.DescriptionModeGenerateParam, token: str = Depends(get_token)
):
    max_retries = len(suno_auth.account_manager.active_accounts)
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 首先检查账户积分
            credits_info = await get_credits(token)
            if credits_info["credits_left"] == 0:
                # 积分不足，切换到下一个账户
                suno_auth.handle_insufficient_credits()
                time.sleep(1)
                token = suno_auth.get_token()
                retry_count += 1
                continue
            
            # 有足够积分，进行生成
            resp = await generate_music(data.dict(), token)
            return resp
            
        except Exception as e:
            traceback.print_exc()
            retry_count += 1
            if retry_count >= max_retries:
                raise HTTPException(
                    detail="All accounts exhausted or error occurred",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            suno_auth.handle_insufficient_credits()
            time.sleep(1)
            token = suno_auth.get_token()
            continue
    
    raise HTTPException(
        detail="All accounts exhausted",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


@app.get("/feed/{aid}")
async def fetch_feed(aid: str, token: str = Depends(get_token)):
    try:
        resp = await get_feed(aid, token)
        return resp
    except Exception as e:
        raise HTTPException(
            detail=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.post("/generate/lyrics/")
async def generate_lyrics_post(request: Request, token: str = Depends(get_token)):
    req = await request.json()
    prompt = req.get("prompt")
    if prompt is None:
        raise HTTPException(
            detail="prompt is required", status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        resp = await generate_lyrics(prompt, token)
        return resp
    except Exception as e:
        raise HTTPException(
            detail=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get("/lyrics/{lid}")
async def fetch_lyrics(lid: str, token: str = Depends(get_token)):
    try:
        resp = await get_lyrics(lid, token)
        return resp
    except Exception as e:
        raise HTTPException(
            detail=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.get("/get_credits")
async def fetch_credits(token: str = Depends(get_token)):
    try:
        resp = await get_credits(token)
        return resp
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            detail=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@app.on_event("startup")
async def startup_event():
    print("Starting application...")
    # 重新加载账号状态
    suno_auth.account_manager.load_accounts()
    suno_auth.account_manager.load_disabled_accounts()
    suno_auth.account_manager.update_active_accounts()
    
    print(f"Loaded {len(suno_auth.account_manager.accounts)} total accounts")
    print(f"Found {len(suno_auth.account_manager.disabled_accounts)} disabled accounts")
    print(f"Active accounts: {len(suno_auth.account_manager.active_accounts)}")

    # 启动keep_alive
    start_keep_alive(suno_auth)
