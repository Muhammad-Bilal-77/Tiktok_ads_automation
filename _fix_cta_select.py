
import re

with open('create_campaign.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Old selection block to replace (from "# Now click the first matching option" to end of fallback)
old_block = '''                                            # Now click the first matching option
                                            for opt_sel in [
                                                '.vi-select-tree-dropdown-horizontal .vi-select-tree-item',
                                                '.vi-select-tree-dropdown .vi-select-tree-item',
                                                '[class*="vi-select-tree-item"]',
                                            ]:
                                                try:
                                                    for opt_el in driver.find_elements(By.CSS_SELECTOR, opt_sel):
                                                        opt_text = (opt_el.text or '').strip().lower()
                                                        if 'apply now' in opt_text:
                                                            r = driver.execute_script(
                                                                'var r=arguments[0].getBoundingClientRect();'
                                                                'return r.width>0&&r.height>0;', opt_el)
                                                            if r:
                                                                driver.execute_script(
                                                                    'arguments[0].scrollIntoView({block:"nearest"});',
                                                                    opt_el)
                                                                time.sleep(0.2)
                                                                driver.execute_script(
                                                                    'arguments[0].click();', opt_el)
                                                                log_success('[CTA] Selected \\'Apply now\\'!')
                                                                cta_selected = True
                                                                break
                                                except Exception:
                                                    pass
                                                if cta_selected:
                                                    break

                                            if not cta_selected:
                                                # Fallback: XPath span/div text match
                                                try:
                                                    for el in driver.find_elements(
                                                            By.XPATH,
                                                            '//*[contains(@class,"vi-select-tree-item") and '
                                                            'normalize-space(.)="Apply now"]'):
                                                        r = driver.execute_script(
                                                            'var r=arguments[0].getBoundingClientRect();'
                                                            'return r.width>0&&r.height>0;', el)
                                                        if r:
                                                            driver.execute_script('arguments[0].click();', el)
                                                            log_success('[CTA] Selected \\'Apply now\\' (XPath)!')
                                                            cta_selected = True
                                                            break
                                                except Exception as xe:
                                                    log_error(f'[CTA] XPath select error: {xe}')'''

new_block = '''                                            # Click the matching option using specific selectors
                                            # Structure: label[role=checkbox] > span > div > div.index_nodeContent > div "Apply now"
                                            xpaths_opt = [
                                                # Checkbox label containing "Apply now"
                                                '//label[@role="checkbox" and contains(.,"Apply now")]',
                                                # nodeContent div with exact text
                                                '//*[contains(@class,"index_nodeContent") and normalize-space(.)="Apply now"]',
                                                # Any div with exact text "Apply now" in the dropdown
                                                '//div[contains(@class,"vi-select-tree-dropdown")]//div[normalize-space(.)="Apply now"]',
                                                # Generic: any visible element with text "Apply now"
                                                '//*[normalize-space(.)="Apply now"]',
                                            ]
                                            for xp_opt in xpaths_opt:
                                                if cta_selected:
                                                    break
                                                try:
                                                    for opt_el in driver.find_elements(By.XPATH, xp_opt):
                                                        r = driver.execute_script(
                                                            'var r=arguments[0].getBoundingClientRect();'
                                                            'return r.width>0&&r.height>0;', opt_el)
                                                        if r:
                                                            driver.execute_script(
                                                                'arguments[0].scrollIntoView({block:"nearest"});',
                                                                opt_el)
                                                            time.sleep(0.2)
                                                            driver.execute_script('arguments[0].click();', opt_el)
                                                            log_success(f'[CTA] Selected \\'Apply now\\' ({xp_opt[:40]})!')
                                                            cta_selected = True
                                                            break
                                                except Exception:
                                                    pass'''

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    with open('create_campaign.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced selection block successfully")
else:
    print("ERROR: Old block not found — check whitespace/encoding")
