import aiohttp
import logging
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import *
from astrbot.api.all import *

logger = logging.getLogger("astrbot")

@register("nzm", "thTag", "哪煮米域名比价插件", "1.1.3", "https://github.com/thTag/astrbot_plugin_nzm")
class NazhumiPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = context.get_config()
        self.api_base = "https://www.nazhumi.com/api/v1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    metadata = {
        "config_schema": {
            "default_order": {
                "type": "string",
                "label": "默认排序方式",
                "default": "new",
                "options": ["new", "renew", "transfer"],
                "description": "new: 注册, renew: 续费, transfer: 转入"
            }
        }
    }

    @filter.command("nzm")
    async def query_by_domain(self, event: AstrMessageEvent, domain: str):
        '''查询后缀比价。用法: /nzm com'''
        if not domain:
            yield event.plain_result("💡 请输入后缀，如: /nzm com")
            return
            
        order = self.config.get('default_order', 'new')
        params = {"domain": domain.strip('.'), "order": order}
        
        logger.info(f"[NZM] 正在请求 API: {self.api_base} params={params}")

        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(self.api_base, params=params) as resp:
                    if resp.status != 200:
                        yield event.plain_result(f"❌ 哪煮米接口异常 (状态码: {resp.status})")
                        return
                        
                    data = await resp.json()
                    
                    # 兼容处理：如果返回的是字典
                    if isinstance(data, dict):
                        logger.info(f"[NZM] 收到字典数据，键名为: {list(data.keys())}")
                        # 逻辑：如果文档里提到的 registrarname 在顶层，说明直接返回了数据对象
                        if "registrarname" in data:
                            data = [data]
                        # 或者尝试寻找嵌套的列表（有些 API 会包一层）
                        else:
                            for k in ["data", "results", "list"]:
                                if isinstance(data.get(k), list):
                                    data = data[k]
                                    break

                    if not data or not isinstance(data, list):
                        yield event.plain_result(f"🔍 哪煮米未返回 .{domain} 的有效比价列表。")
                        return
                    
                    msg = f"📊 .{domain} 比价结果 (按{self._translate_order(order)}排序):\n"
                    for item in data:
                        price = f"{item['currency']} {item['new']}" if item.get('new') != 'n/a' else "N/A"
                        renew = f"{item['currency']} {item['renew']}" if item.get('renew') != 'n/a' else "N/A"
                        msg += f"• {item['registrarname']}: 注册 {price} / 续费 {renew}\n"
                    
                    msg += "\n数据来源: nazhumi.com"
                    yield event.plain_result(msg)
            except Exception as e:
                logger.error(f"[NZM] 插件运行出错", exc_info=True)
                yield event.plain_result(f"⚠️ 查询出错: {str(e)}")

    @filter.command("nzm_reg")
    async def query_by_registrar(self, event: AstrMessageEvent, reg: str):
        '''查注册商最便宜后缀。用法: /nzm_reg aliyun'''
        if not reg:
            yield event.plain_result("💡 请输入注册商代码，如: /nzm_reg aliyun")
            return

        order = self.config.get('default_order', 'new')
        params = {"registrar": reg, "order": order}
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(self.api_base, params=params) as resp:
                    data = await resp.json()
                    if isinstance(data, dict) and "registrarname" in data:
                        data = [data] # 同上兼容逻辑
                    
                    if not data or not isinstance(data, list):
                        yield event.plain_result(f"❌ 未找到注册商 {reg} 的数据。")
                        return
                    
                    msg = f"🏢 {data[0]['registrarname']} 最便宜后缀 (按{self._translate_order(order)}排序):\n"
                    for item in data:
                        msg += f"• .{item['domain']}: 注册 {item['currency']} {item['new']}\n"
                    yield event.plain_result(msg)
            except Exception as e:
                yield event.plain_result(f"⚠️ 查询出错: {str(e)}")

    def _translate_order(self, order):
        mapping = {"new": "注册价格", "renew": "续费价格", "transfer": "转入价格"}
        return mapping.get(order, "价格")
