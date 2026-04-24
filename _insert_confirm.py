
confirm_block = """\n                        # -- Sidebar Confirm button (hybrid-drawer-footer-submit-button) --\n                        if d2_clicked:\n                            log_info('[CONFIRM] Waiting for sidebar Confirm button...')\n                            time.sleep(2)\n                            confirmed = False\n                            for _cf in range(6):\n                                try:\n                                    cf_el = None\n                                    # Strategy A: exact data-testid via Selenium\n                                    try:\n                                        for el in driver.find_elements(By.CSS_SELECTOR,\n                                                '[data-testid=\"hybrid-drawer-footer-submit-button\"]'):\n                                            r = driver.execute_script(\n                                                'var r=arguments[0].getBoundingClientRect();'\n                                                'return r.width>0&&r.height>0;', el)\n                                            if r:\n                                                cf_el = el\n                                                break\n                                    except Exception:\n                                        pass\n\n                                    # Strategy B: XPath in footer-operation div\n                                    if not cf_el:\n                                        try:\n                                            xp = '//*[contains(@class,\"footer-operation\")]//button[normalize-space(.)=\"Confirm\"]'\n                                            for el in driver.find_elements(By.XPATH, xp):\n                                                r = driver.execute_script(\n                                                    'var r=arguments[0].getBoundingClientRect();'\n                                                    'return r.width>0&&r.height>0;', el)\n                                                if r:\n                                                    cf_el = el\n                                                    break\n                                        except Exception:\n                                            pass\n\n                                    if cf_el:\n                                        driver.execute_script(\n                                            'arguments[0].scrollIntoView({block:\"nearest\"});', cf_el)\n                                        time.sleep(0.2)\n                                        driver.execute_script('arguments[0].click();', cf_el)\n                                        log_success('[CONFIRM] Clicked sidebar Confirm button!')\n                                        confirmed = True\n                                        time.sleep(2)\n                                        break\n                                    else:\n                                        log_info(f'[CONFIRM] Confirm not found attempt {_cf+1}...')\n                                        time.sleep(1)\n                                except Exception as cf_err:\n                                    log_error(f'[CONFIRM] Error attempt {_cf+1}: {cf_err}')\n                                    time.sleep(1)\n\n                            if not confirmed:\n                                log_error('[CONFIRM] Could not click sidebar Confirm after 6 attempts.')\n"""

with open('create_campaign.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line "if not d2_clicked:" and insert the confirm block right after it
insert_after = None
for i, line in enumerate(lines):
    if "if not d2_clicked:" in line:
        insert_after = i + 1  # insert after the log_error line on next line
        break

if insert_after is None:
    print("ERROR: Could not find insertion point")
else:
    # Find the log_error line right after "if not d2_clicked:"
    # The block goes: "if not d2_clicked:\n    log_error(...)\n"  — insert after log_error
    insert_at = insert_after + 1  # skip the log_error line too
    new_lines = lines[:insert_at] + [confirm_block] + lines[insert_at:]
    with open('create_campaign.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Inserted confirm block after line {insert_at}")
