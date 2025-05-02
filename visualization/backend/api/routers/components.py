from fastapi import APIRouter


router = APIRouter(prefix="/components", tags=["components"])


@router.get("")
async def get_visualizatioin():
    return True
    
