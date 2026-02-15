"""UPS 设备列表 API"""
from fastapi import APIRouter, HTTPException
from config import settings

router = APIRouter()


@router.get("/ups/list")
async def list_ups():
    """列出所有 UPS 设备"""
    from services.nut_client import create_nut_client
    
    # 创建临时客户端
    client = create_nut_client(
        settings.nut_host,
        settings.nut_port,
        settings.nut_username,
        settings.nut_password,
        settings.nut_ups_name,
        settings.mock_mode
    )
    
    try:
        await client.connect()
        ups_list = await client.list_ups()
        await client.disconnect()
        
        return {"ups_list": ups_list}
    
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to list UPS devices: {str(e)}")
