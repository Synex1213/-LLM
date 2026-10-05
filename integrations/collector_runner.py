"""Run the installed upstream cnki-metadata-exporter with small UI-compatibility patches.

The upstream package itself remains installed in site-packages.  This wrapper only
patches browser selection and CNKI's currently duplicated/hidden professional-search
controls before delegating to the upstream native exporter.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from cnki_metadata_exporter.exporter import CNKIMetadataExporter
import cnki_metadata_exporter.exporter as exporter_mod
import cnki_metadata_exporter.native_export as native_export


async def _first_visible_locator(self, page, selectors):
    for selector in selectors:
        locator=page.locator(selector)
        try:
            count=await locator.count()
        except Exception:
            continue
        for index in range(count):
            item=locator.nth(index)
            try:
                if await item.is_visible(timeout=300):
                    return item
            except Exception:
                continue
    return None


async def _dump_search_debug(self, page, label):
    try:
        await page.screenshot(path=str(self.logs_dir/f"{label}.png"),full_page=True)
    except Exception:
        pass
    try:
        (self.logs_dir/f"{label}.html").write_text(await page.content(),encoding="utf-8")
    except Exception:
        pass


async def _launch(self):
    self.profile_dir.mkdir(parents=True,exist_ok=True)
    self._playwright=await exporter_mod.async_playwright().start()
    kwargs=dict(
        user_data_dir=str(self.profile_dir),headless=self.headless,accept_downloads=True,
        ignore_https_errors=True,locale="zh-CN",viewport={"width":1440,"height":960},
        args=["--disable-dev-shm-usage","--disable-background-timer-throttling","--disable-backgrounding-occluded-windows","--disable-renderer-backgrounding"],
    )
    for channel,label in (("msedge","Microsoft Edge"),("chrome","Google Chrome")):
        try:
            self.context=await self._playwright.chromium.launch_persistent_context(channel=channel,**kwargs)
            self.log(f"浏览器：使用系统 {label}")
            return
        except Exception as exc:
            self.log(f"系统 {label} 启动失败：{exc}")
    self.context=await self._playwright.chromium.launch_persistent_context(**kwargs)
    self.log("浏览器：使用 Playwright Chromium")


async def _open_professional_search(self,page):
    await page.goto(exporter_mod.CNKI_ADVANCED,wait_until="domcontentloaded",timeout=60000)
    await self.wait_for_human_verification(page)
    tab=await self._first_visible_locator(page,[".search-classify-menu li[name='majorSearch']","li[name='majorSearch']","[name='majorSearch']"])
    if tab is None:
        tabs=page.get_by_text("专业检索",exact=True)
        for i in range(await tabs.count()):
            item=tabs.nth(i)
            try:
                if await item.is_visible(timeout=300):
                    tab=item; break
            except Exception:
                continue
    if tab is None:
        await self._dump_search_debug(page,"professional-search-tab-missing")
        raise RuntimeError("未找到可见的知网专业检索入口")
    for attempt in range(3):
        try:
            await tab.click(force=True)
        except Exception:
            try: await tab.evaluate("e => e.click()")
            except Exception: pass
        await page.wait_for_timeout(600+attempt*500)
        box=await self._first_visible_locator(page,["textarea.textarea-major.majorSearch","textarea.majorSearch","textarea.textarea-major","#expertvalue","#txt_SearchText","textarea"])
        if box is not None:
            return
    count=await page.locator("textarea.textarea-major, textarea.majorSearch, textarea").count()
    await self._dump_search_debug(page,"professional-search-input-hidden")
    raise RuntimeError(f"专业检索标签已点击，但没有可见检索框（匹配到 {count} 个隐藏/不可见 textarea）。已保存 logs 调试文件。")


async def _submit_professional_query(self,page,query):
    await self.open_professional_search(page)
    box=await self._first_visible_locator(page,["textarea.textarea-major.majorSearch","textarea.majorSearch","textarea.textarea-major","#expertvalue","#txt_SearchText","input[name='expertvalue']","textarea"])
    if box is None:
        await self._dump_search_debug(page,"professional-search-query-box-missing")
        raise RuntimeError("未找到可见的知网专业检索式输入框")
    await box.fill(query)
    bilingual=page.locator('.gradeSearch input[data-id="EN"]:checked').first
    if await bilingual.count():
        await bilingual.uncheck()
    button=page.locator(".search-middle input.btn-search:visible, input.btn-search:visible").first
    if not await button.count():
        button=page.get_by_role("button",name=re.compile(r"检索|搜索")).first
    if not await button.count():
        raise RuntimeError("未找到知网专业检索按钮")
    await button.click()
    try:
        await page.locator("span.pagerTitleCell, table.result-table-list, p.no-content").first.wait_for(state="visible",timeout=45000)
    except PlaywrightTimeoutError:
        await self.wait_for_human_verification(page)
    await self.wait_for_human_verification(page)


async def _set_publish_date_range(self, page, start_year: int | None, end_year: int | None):
    """Set CNKI KNS8 publication-date controls (#datebox0/#datebox1).

    The current page exposes readonly text inputs. We set the DOM value directly and dispatch
    the same input/change events used by the page. This keeps year filtering out of the
    professional-search expression (YE is not a current KNS8 field code).
    """
    if not start_year or not end_year:
        return
    start_value = f"{int(start_year):04d}-01-01"
    end_value = f"{int(end_year):04d}-12-31"
    start_box = page.locator("#datebox0").first
    end_box = page.locator("#datebox1").first
    if not await start_box.count() or not await end_box.count():
        await self._dump_search_debug(page, "publish-date-controls-missing")
        raise RuntimeError("未找到知网发表时间控件 #datebox0 / #datebox1")
    script = """([el, value]) => {
        el.removeAttribute('readonly');
        el.value = value;
        el.setAttribute('value', value);
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
        el.dispatchEvent(new Event('blur', {bubbles:true}));
        if (window.jQuery) {
            try { window.jQuery(el).val(value).trigger('input').trigger('change').trigger('blur'); } catch(e) {}
        }
    }"""
    await start_box.evaluate(script, start_value)
    await end_box.evaluate(script, end_value)
    got_start = await start_box.input_value()
    got_end = await end_box.input_value()
    if got_start != start_value or got_end != end_value:
        await self._dump_search_debug(page, "publish-date-controls-not-set")
        raise RuntimeError(f"发表时间控件写入失败：{got_start!r} -- {got_end!r}")
    self.log(f"发表时间：{start_value} -- {end_value}")


async def _submit_collection_query(self, page, collection):
    await self.open_professional_search(page)
    box = await self._first_visible_locator(page, [
        "textarea.textarea-major.majorSearch", "textarea.majorSearch", "textarea.textarea-major",
        "#expertvalue", "#txt_SearchText", "input[name='expertvalue']", "textarea"
    ])
    if box is None:
        await self._dump_search_debug(page, "professional-search-query-box-missing")
        raise RuntimeError("未找到可见的知网专业检索式输入框")
    await box.fill(str(collection["query"]))
    await self._set_publish_date_range(page, collection.get("start_year"), collection.get("end_year"))
    bilingual = page.locator('.gradeSearch input[data-id="EN"]:checked').first
    if await bilingual.count():
        await bilingual.uncheck()
    button = page.locator(".search-middle input.btn-search:visible, input.btn-search:visible").first
    if not await button.count():
        button = page.get_by_role("button", name=re.compile(r"检索|搜索")).first
    if not await button.count():
        raise RuntimeError("未找到知网专业检索按钮")
    await button.click()
    try:
        await page.locator("span.pagerTitleCell, table.result-table-list, p.no-content").first.wait_for(
            state="visible", timeout=45000
        )
    except PlaywrightTimeoutError:
        await self.wait_for_human_verification(page)
    await self.wait_for_human_verification(page)


async def _search_collection(self, page, collection):
    """Upstream-compatible search loop with KNS8 LY query + publication-date controls."""
    last_error = None
    for attempt in range(1, 5):
        try:
            await self._submit_collection_query(page, collection)
            total = await self.result_count(page)
            if total > 0:
                pages, per_page = await self.set_page_size_stable(page, total, 50)
            else:
                _, pages = await self.page_info(page)
                per_page = await self.current_row_count(page)
            if total > 0 and per_page > 0:
                return total, pages, per_page
            body = await self._body(page)
            self.log(
                f"{collection['id']} 第 {attempt} 次检索未读取到有效结果"
                f"（命中 {total}，当前页 {per_page} 条），准备重试"
            )
            (self.logs_dir / f"{collection['id']}-search-attempt-{attempt}.txt").write_text(
                body[:20000], encoding="utf-8"
            )
        except Exception as exc:
            last_error = exc
            self.log(f"{collection['id']} 第 {attempt} 次检索失败：{exc}")
        await page.wait_for_timeout(attempt * 3000)
    if last_error:
        raise RuntimeError(f"{collection['id']} 多次检索失败") from last_error
    raise RuntimeError(f"{collection['id']} 多次检索均未返回有效记录")


CNKIMetadataExporter._first_visible_locator=_first_visible_locator
CNKIMetadataExporter._dump_search_debug=_dump_search_debug
CNKIMetadataExporter.launch=_launch
CNKIMetadataExporter.open_professional_search=_open_professional_search
CNKIMetadataExporter.submit_professional_query=_submit_professional_query
CNKIMetadataExporter._set_publish_date_range=_set_publish_date_range
CNKIMetadataExporter._submit_collection_query=_submit_collection_query
CNKIMetadataExporter.search_collection=_search_collection

if __name__ == "__main__":
    native_export.main()
