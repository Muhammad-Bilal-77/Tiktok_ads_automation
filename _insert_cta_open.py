
cta_open_block = """
                            # -- Click the CTA container to open the dropdown list --
                            if cta_cleared:
                                log_info('[CTA] Clicking CTA container to open dropdown...')
                                time.sleep(0.8)
                                cta_opened = False
                                for _cto in range(6):
                                    try:
                                        cto_el = None
                                        # Strategy A: the container div (tabindex=0, holds the selected tags)
                                        for sel in [
                                            'div.vi-select-tree-inside-container',
                                            '[data-testid="creative_cta_dynamic_select"]',
                                            '[data-testid*="select-tree-index"] .vi-select-tree-inside',
                                        ]:
                                            try:
                                                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                                                    r = driver.execute_script(
                                                        'var r=arguments[0].getBoundingClientRect();'
                                                        'return r.width>0&&r.height>0;', el)
                                                    if r:
                                                        cto_el = el
                                                        break
                                            except Exception:
                                                pass
                                            if cto_el:
                                                break

                                        if cto_el:
                                            driver.execute_script(
                                                'arguments[0].scrollIntoView({block:"center"});', cto_el)
                                            time.sleep(0.3)
                                            driver.execute_script('arguments[0].click();', cto_el)
                                            log_success('[CTA] Clicked CTA container — dropdown should open!')
                                            cta_opened = True
                                            time.sleep(1)
                                            break
                                        else:
                                            log_info(f'[CTA] Container not found attempt {_cto+1}...')
                                            time.sleep(0.8)
                                    except Exception as cto_err:
                                        log_error(f'[CTA] Open dropdown error attempt {_cto+1}: {cto_err}')
                                        time.sleep(0.8)

                                if not cta_opened:
                                    log_error('[CTA] Could not open CTA dropdown.')
"""

with open('create_campaign.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find "if not cta_cleared:" line and insert the block right after the log_error
insert_at = None
for i, line in enumerate(lines):
    if "Could not click Call to action clear icon" in line:
        insert_at = i + 1
        break

if insert_at is None:
    print("ERROR: Could not find insertion point")
else:
    new_lines = lines[:insert_at] + [cta_open_block + '\n'] + lines[insert_at:]
    with open('create_campaign.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Inserted CTA-open block after line {insert_at}")
