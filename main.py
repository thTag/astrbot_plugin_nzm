import aiohttp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import *

@register("nzm", "thTag", "哪煮米域名比价插件", "1.0.0", "https://github.com/thTag/astrbot_plugin_nzm")
class NazhumiPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_base = "https://www.nazhumi.com/api/v1"

    @filter.command("nzm")
    async def query_by_domain(self, event: AstrMessageEvent, domain: str):
        '''查询后缀比价。用法: /nzm com'''
        if not domain:
            yield event.plain_result("💡 请输入后缀，如: /nzm com")
            return
            
        params = {"domain": domain.strip('.')}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.api_base, params=params) as resp:
                    if resp.status != 200:
                        yield event.plain_result("❌ 哪煮米接口暂时不可用。")
                        return
                    data = await resp.json()
                    if not data or not isinstance(data, list):
                        yield event.plain_result(f"🔍 未找到 .{domain} 的相关数据。")
                        return
                    
                    msg = f"📊 .{domain} 注册比价 Top {len(data)}:\n"
                    for item in data:
                        price = f\"{item['currency']} {item['new']}\" if item['new'] != \"n/a\" else \"N/A\"
                        renew = f\"{item['currency']} {item['renew']}\" if item['renew'] != \"n/a\" else \"N/A\"
                        msg += f"• {item['registrarname']}: 注册 {price} / 续费 {renew}\n"
                    
                    msg += "\n数据来源: nazhumi.com"
                    yield event.plain_result(msg)
            except Exception as e:
                yield event.plain_result(f"⚠️ 查询出错: {str(e)}")

    @filter.command("nzm_reg")
    async def query_by_registrar(self, event: AstrMessageEvent, reg: str):
        '''查注册商最便宜后缀。用法: /nzm_reg aliyun'''
        if not reg:
            yield event.plain_result("💡 请输入注册商代码，如: /nzm_reg aliyun")
            return

        params = {"registrar": reg}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.api_base, params=params) as resp:
                    if resp.status != 200:
                        yield event.plain_result("❌ 哪煮米接口暂时不可用。")
                        return
                    data = await resp.json()
                    if not data or not isinstance(data, list):
                        yield event.plain_result(f"❌ 未找到注册商 {reg} 的数据。")
                        return
                    
                    msg = f"🏢 {data[0]['registrarname']} 最便宜后缀:\n"
                    for item in data:
                        msg += f"• .{item['domain']}: 注册 {item['currency']} {item['new']}\n"
                    yield event.plain_result(msg)
            except Exception as e:
                yield event.plain_result(f"⚠️ 查询出错: {str(e)}")
