
cta_select_block = """
                                # -- Type 'Apply now' in search box and select it --
                                if cta_opened:
                                    log_info('[CTA] Typing \\'Apply now\\' in dropdown search...')
                                    time.sleep(0.8)
                                    cta_selected = False
                                    try:
                                        # Find the search input inside the now-open dropdown
                                        search_inp = None
                                        for sel in [
                                            'input.vi-input__inner[placeholder="Search or select"]',
                                            'input[data-testid*="select-tree-index"]',
                                            '.vi-select-tree-dropdown input',
                                            '.vi-select-tree-dropdown-input input',
                                        ]:
                                            try:
                                                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                                                    r = driver.execute_script(
                                                        'var r=arguments[0].getBoundingClientRect();'
                                                        'return r.width>0&&r.height>0;', el)
                                                    if r:
                                                        search_inp = el
                                                        break
                                            except Exception:
                                                pass
                                            if search_inp:
                                                break

                                        if search_inp:
                                            search_inp.click()
                                            time.sleep(0.3)
                                            search_inp.send_keys('Apply now')
                                            log_info('[CTA] Typed \\'Apply now\\' in search box.')
                                            time.sleep(1.5)  # wait for results to filter

                                            # Now click the first matching option
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
                                                    log_error(f'[CTA] XPath select error: {xe}')

                                        else:
                                            log_error('[CTA] Search input not found in dropdown.')

                                    except Exception as cs_err:
                                        log_error(f'[CTA] Select error: {cs_err}')

                                    if not cta_selected:
                                        log_error('[CTA] Could not select \\'Apply now\\'.')
                                    else:
                                        time.sleep(0.5)
"""

with open('create_campaign.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find "if not cta_opened:" line and insert the block right after the log_error on the next line
insert_at = None
for i, line in enumerate(lines):
    if "Could not open CTA dropdown" in line:
        insert_at = i + 1
        break

if insert_at is None:
    print("ERROR: Could not find insertion point")
else:
    new_lines = lines[:insert_at] + [cta_select_block + '\n'] + lines[insert_at:]
    with open('create_campaign.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Inserted CTA select block after line {insert_at}")
