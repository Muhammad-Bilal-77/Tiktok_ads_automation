
cta_block = """
                        # -- Scroll to 'Call to action' and click clear (right-icon) --
                        if confirmed:
                            log_info('[CTA] Scrolling to Call to action section...')
                            time.sleep(1.5)
                            try:
                                # Scroll the page down to expose the CTA section
                                driver.execute_script("window.scrollBy(0, 400);")
                                time.sleep(1)
                            except Exception:
                                pass

                            cta_cleared = False
                            for _cta in range(6):
                                try:
                                    cta_el = None
                                    # Strategy A: i.right-icon that is NOT the arrow-down (= clear btn)
                                    # inside the vi-select-tree-inside-container
                                    selectors = [
                                        'i.right-icon:not(.vi-icon-arrow-down)',
                                        '[data-testid*="select-tree-container-inside"].right-icon',
                                        'i[data-testid*="select-tree-container-inside"]',
                                    ]
                                    for sel in selectors:
                                        try:
                                            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                                                r = driver.execute_script(
                                                    'var r=arguments[0].getBoundingClientRect();'
                                                    'return r.width>=0&&r.height>=0&&r.top>=0;', el)
                                                if r:
                                                    cta_el = el
                                                    break
                                        except Exception:
                                            pass
                                        if cta_el:
                                            break

                                    if cta_el:
                                        driver.execute_script(
                                            'arguments[0].scrollIntoView({block:"center"});', cta_el)
                                        time.sleep(0.3)
                                        driver.execute_script('arguments[0].click();', cta_el)
                                        log_success('[CTA] Clicked Call to action clear icon!')
                                        cta_cleared = True
                                        time.sleep(1)
                                        break
                                    else:
                                        log_info(f'[CTA] Clear icon not found attempt {_cta+1}...')
                                        time.sleep(0.8)
                                except Exception as cta_err:
                                    log_error(f'[CTA] Error attempt {_cta+1}: {cta_err}')
                                    time.sleep(0.8)

                            if not cta_cleared:
                                log_error('[CTA] Could not click Call to action clear icon.')
"""

with open('create_campaign.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find "if not confirmed:" line and insert after the log_error that follows it
insert_at = None
for i, line in enumerate(lines):
    if "Could not click sidebar Confirm after 6 attempts" in line:
        insert_at = i + 1
        break

if insert_at is None:
    print("ERROR: Could not find insertion point")
else:
    new_lines = lines[:insert_at] + [cta_block + '\n'] + lines[insert_at:]
    with open('create_campaign.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Inserted CTA block after line {insert_at}")
