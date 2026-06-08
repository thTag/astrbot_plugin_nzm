import aiohttp
import logging
import json
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import *
from astrbot.api.all import *

logger = logging.getLogger("astrbot")

@register("nzm", "thTag", "哪煮米域名比价插件", "1.1.5", "https://github.com/thTag/astrbot_plugin_nzm")
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
        
        logger.info(f"[NZM] 请求 API: {params}")

        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(self.api_base, params=params) as resp:
                    if resp.status != 200:
                        yield event.plain_result(f"❌ 接口异常: {resp.status}")
                        return
                    
                    text = await resp.text()
                    try:
                        raw_data = json.loads(text)
                    except:
                        yield event.plain_result("❌ 接口返回了非 JSON 格式。")
                        return

                    # 根据你 curl 的数据结构提取列表
                    final_list = []
                    if isinstance(raw_data, dict):
                        inner_data = raw_data.get("data", {})
                        if isinstance(inner_data, dict):
                            # 数据实际存放在 data.price 里
                            final_list = inner_data.get("price", [])
                        elif isinstance(inner_data, list):
                            final_list = inner_data
                    elif isinstance(raw_data, list):
                        final_list = raw_data

                    if not final_list or not isinstance(final_list, list):
                        yield event.plain_result(f"🔍 未找到 .{domain} 的有效比价结果。")
                        return
                    
                    msg = f"📊 .{domain} 比价结果 ({self._translate_order(order)}):\n"
                    for item in final_list[:10]: # 最多展示10条
                        reg_name = item.get('registrarname', '未知服务商')
                        cur = item.get('currency', 'usd').upper()
                        new_p = item.get('new', 'n/a')
                        ren_p = item.get('renew', 'n/a')
                        
                        price_str = f"{cur} {new_p}" if str(new_p).lower() != 'n/a' else "N/A"
                        renew_str = f"{cur} {ren_p}" if str(ren_p).lower() != 'n/a' else "N/A"
                        msg += f"• {reg_name}: {price_str} (续费 {renew_str})\n"
                    
                    msg += "\n数据来源: nazhumi.com"
                    yield event.plain_result(msg)
            except Exception as e:
                logger.error("[NZM] 插件运行报错", exc_info=True)
                yield event.plain_result(f"⚠️ 报错了: {str(e)}")

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
                    if resp.status != 200:
                        yield event.plain_result(f"❌ 接口异常: {resp.status}")
                        return
                    data = await resp.json()
                    
                    final_list = []
                    if isinstance(data, dict):
                        inner_data = data.get("data", {})
                        if isinstance(inner_data, dict):
                            # 获取最便宜后缀列表的 key 也是 price 
                            final_list = inner_data.get("price", [])
                        elif isinstance(inner_data, list):
                            final_list = inner_data
                    elif isinstance(data, list):
                        final_list = data
                    
                    if not final_list or not isinstance(final_list, list):
                        yield event.plain_result(f"❌ 未找到注册商 {reg} 的数据。")
                        return
                    
                    # 尝试从第一条数据获取注册商名称，若无则使用原始代码
                    reg_show_name = final_list[0].get('registrarname', reg.upper())
                    msg = f"🏢 {reg_show_name} 最便宜后缀 ({self._translate_order(order)}):\n"
                    for item in final_list:
                        cur = item.get('currency', 'usd').upper()
                        price = f"{cur} {item.get('new', 'n/a')}"
                        msg += f"• .{item.get('domain')}: 注册 {price}\n"
                    yield event.plain_result(msg)
            except Exception as e:
                yield event.plain_result(f"⚠️ 查询出错: {str(e)}")

    def _translate_order(self, order):
        mapping = {"new": "注册", "renew": "续费", "transfer": "转入"}
        return mapping.get(order, "价格")
