# Handler for messages (acting as /button and /filter logic, excluding commands)
@dp.message(F.text, ~F.text.startswith('/'))
@dp.channel_post(F.text, ~F.text.startswith('/'))
async def convert_link_to_button(message: types.Message):
    logger.info(f"Received full message text: {message.text}")
    logger.info(f"Chat type: {message.chat.type}")
    logger.info(f"Original message ID: {message.message_id}")
    logger.info(f"Forwarded from: {message.forward_from_chat}")
    logger.info(f"Entities: {message.entities}")
    logger.info(f"Filter enabled state: {filter_enabled}")
    logger.info(f"Current PassValue: {PassValue}")
    logger.info(f"Current RangeLow: {RangeLow}")

    if message.forward_from_chat:
        logger.info(f"Message is forwarded from chat: {message.forward_from_chat.title}")

    ca = None
    text = message.text
    if message.entities:
        for entity in message.entities:
            if entity.type in ["url", "text_link"]:
                url = entity.url if entity.type == "text_link" else text[entity.offset:entity.offset + entity.length]
                logger.info(f"Found URL: {url}")
                ca_match = re.search(r'[A-Za-z0-9]{44}', url)
                if ca_match:
                    ca = ca_match.group(0)
                    logger.info(f"Extracted CA: {ca}")
                break

    # If no URL entity, try to find CA in plain text
    if not ca:
        ca_match = re.search(r'[A-Za-z0-9]{44}', text)
        if ca_match:
            ca = ca_match.group(0)
            logger.info(f"Extracted CA from plain text: {ca}")

    # Extract BuyPercent, SellPercent, and other filter values
    has_buy_sell = False
    buy_percent = None
    sell_percent = None
    dev_sold = None  # "Yes" or "No"
    dev_sold_left_value = None  # Percentage left if dev_sold is "No"
    top_10 = None
    snipers = None
    bundles = None
    insiders = None
    kols = None
    lines = [line.strip() for line in text.replace('\r\n', '\n').split('\n') if line.strip()]
    logger.info(f"Lines to check: {lines}")

    for line in lines:
        logger.info(f"Checking line: '{line}'")
        match_bs = re.search(r'├?Sum\s*🅑:\s*(\d+\.?\d*)%\s*[\|]\s*Sum\s*🅢:\s*(\d+\.?\d*)%', line)
        if match_bs:
            has_buy_sell = True
            buy_percent = float(match_bs.group(1))
            sell_percent = float(match_bs.group(2))
            logger.info(f"Found BuyPercent and SellPercent: {match_bs.group(0)} with groups: {match_bs.groups()}")
            continue

        # Dev sold (Yes/No based on emoji)
        match_dev_yes = re.search(r'├?Dev:\s*✅\s*\(sold\)', line)
        match_dev_no = re.search(r'├?Dev:\s*❌\s*\((\d+\.?\d*)%\s*left\)', line)
        if match_dev_yes:
            dev_sold = "Yes"
            dev_sold_left_value = None
            logger.info(f"Found DevSold: {dev_sold}")
            continue
        elif match_dev_no:
            dev_sold = "No"
            dev_sold_left_value = float(match_dev_no.group(1))
            logger.info(f"Found DevSold: {dev_sold}, Left: {dev_sold_left_value}%")
            continue

        match_top10 = re.search(r'├?Top 10:\s*(\d+\.?\d*)', line)
        if match_top10:
            top_10 = float(match_top10.group(1))
            logger.info(f"Found Top10: {top_10}")
            continue

        match_snipers = re.search(r'├?Sniper:\s*(\d+\.?\d*)', line)
        if match_snipers:
            snipers = float(match_snipers.group(1))
            logger.info(f"Found Snipers: {snipers}")
            continue

        match_bundles = re.search(r'├?Bundle:.*buy\s*(\d+\.?\d*)%', line)
        if match_bundles:
            bundles = float(match_bundles.group(1))
            logger.info(f"Found Bundles: {bundles}")
            continue

        match_insiders = re.search(r'├?🐁Insiders:\s*(\d+\.?\d*)', line)
        if match_insiders:
            insiders = float(match_insiders.group(1))
            logger.info(f"Found Insiders: {insiders}")
            continue

        match_kols = re.search(r'└?🌟KOLs:\s*(\d+\.?\d*)', line)
        if match_kols:
            kols = float(match_kols.group(1))
            logger.info(f"Found KOLs: {kols}")
            continue

    # Process filters if BuyPercent/SellPercent exists
    if has_buy_sell:
        logger.info("Message contains BuyPercent/SellPercent, processing filters")
        if len(lines) >= 2:
            first_line = lines[0]
            second_line = lines[1]
            logger.info(f"Using first line: '{first_line}'")
            logger.info(f"Using second line: '{second_line}'")
        else:
            logger.warning("Source message has fewer than 2 lines, using defaults")
            first_line = "Unknown Token"
            second_line = "🔗 CA: UnknownCA"

        # Calculate BSRatio
        try:
            if sell_percent == 0:
                logger.warning("SellPercent is 0, assuming infinity")
                bs_ratio = float('inf')
            else:
                bs_ratio = buy_percent / sell_percent
                logger.info(f"Calculated BSRatio: {buy_percent} / {sell_percent} = {bs_ratio}")
        except Exception as e:
            logger.error(f"Error calculating BSRatio: {e}")
            bs_ratio = 0

        # Check if required thresholds are set for enabled filters
        missing_vars = []
        if (CheckHighEnabled or CheckLowEnabled) and PassValue is None:
            missing_vars.append("PassValue (use /setupval)")
        if CheckLowEnabled and RangeLow is None:
            missing_vars.append("RangeLow (use /setrangelow)")
        if DevSoldFilterEnabled and DevSoldThreshold is None:
            missing_vars.append("DevSoldThreshold (use /setdevsold Yes|No)")
        if DevSoldFilterEnabled and DevSoldThreshold == "Yes" and dev_sold == "No" and DevSoldLeft is None:
            missing_vars.append("DevSoldLeft (use /setdevsoldleft)")
        if Top10FilterEnabled and Top10Threshold is None:
            missing_vars.append("Top10Threshold (use /settop10)")
        if SniphersFilterEnabled and SnipersThreshold is None:
            missing_vars.append("SnipersThreshold (use /setsnipers)")
        if BundlesFilterEnabled and BundlesThreshold is None:
            missing_vars.append("BundlesThreshold (use /setbundles)")
        if InsidersFilterEnabled and InsidersThreshold is None:
            missing_vars.append("InsidersThreshold (use /setinsiders)")
        if KOLsFilterEnabled and KOLsThreshold is None:
            missing_vars.append("KOLsThreshold (use /setkols)")

        if missing_vars:
            await message.answer(f"⚠️ Please set {', '.join(missing_vars)} before filtering.")
            return

        # Evaluate each filter
        filter_results = []
        all_filters_pass = True
        check_high_pass = None
        check_low_pass = None
        dev_sold_pass = None
        top_10_pass = None
        snipers_pass = None
        bundles_pass = None
        insiders_pass = None
        kols_pass = None

        # BSRatio (OR condition: >= PassValue OR 1 <= BSRatio <= RangeLow)
        if CheckHighEnabled or CheckLowEnabled:
            bs_ratio_pass = (bs_ratio >= PassValue) or (1 <= bs_ratio <= RangeLow) if RangeLow is not None else (bs_ratio >= PassValue)
            filter_results.append(f"BSRatio: {bs_ratio:.2f} {'✅' if bs_ratio_pass else '🚫'} (Threshold: >= {PassValue} or 1 to {RangeLow if RangeLow else 'N/A'})")
            if not bs_ratio_pass:
                all_filters_pass = False
            logger.info(f"BSRatio check: {bs_ratio_pass} - Condition: >= {PassValue} or 1 <= {bs_ratio} <= {RangeLow if RangeLow else 'N/A'}")
        else:
            filter_results.append(f"BSRatio: {bs_ratio:.2f} (Disabled)")

        # DevSold (Yes/No comparison with percentage left check)
        if DevSoldFilterEnabled:
            if dev_sold is None:
                filter_results.append("DevSold: Not found in message 🚫")
                all_filters_pass = False
                logger.info("DevSold: Not found in message")
            elif DevSoldThreshold is None:
                filter_results.append("DevSold: Threshold not set 🚫 (use /setdevsold Yes|No)")
                all_filters_pass = False
                logger.info("DevSold: Threshold not set")
            else:
                logger.info(f"Evaluating DevSold: dev_sold={dev_sold}, DevSoldThreshold={DevSoldThreshold}, dev_sold_left_value={dev_sold_left_value}, DevSoldLeft={DevSoldLeft}")
                if dev_sold == DevSoldThreshold:
                    dev_sold_pass = True
                    filter_results.append(f"DevSold: {dev_sold} {'✅' if dev_sold_pass else '🚫'} (Threshold: {DevSoldThreshold})")
                elif dev_sold == "No" and DevSoldThreshold == "Yes":
                    if DevSoldLeft is None:
                        filter_results.append("DevSold: DevSoldLeft threshold not set 🚫 (use /setdevsoldleft)")
                        dev_sold_pass = False
                    elif dev_sold_left_value is not None:
                        dev_sold_pass = dev_sold_left_value <= DevSoldLeft
                        filter_results.append(
                            f"DevSold: {dev_sold} ({dev_sold_left_value}% left) {'✅' if dev_sold_pass else '🚫'} (Threshold: {DevSoldThreshold}, Left <= {DevSoldLeft}%)"
                        )
                    else:
                        dev_sold_pass = False
                        filter_results.append(f"DevSold: {dev_sold} (No percentage left data) {'✅' if dev_sold_pass else '🚫'} (Threshold: {DevSoldThreshold})")
                else:
                    dev_sold_pass = False
                    filter_results.append(f"DevSold: {dev_sold} {'✅' if dev_sold_pass else '🚫'} (Threshold: {DevSoldThreshold})")
                if not dev_sold_pass:
                    all_filters_pass = False
                logger.info(f"DevSold: {dev_sold_pass}")
        else:
            filter_results.append(f"DevSold: {dev_sold if dev_sold else 'Not found'} (Disabled)")

        # Top10 (Pass if <= Top10Threshold)
        if Top10FilterEnabled and top_10 is not None:
            top_10_pass = top_10 <= Top10Threshold
            filter_results.append(f"Top10: {top_10} {'✅' if top_10_pass else '🚫'} (Threshold: <= {Top10Threshold})")
            if not top_10_pass:
                all_filters_pass = False
            logger.info(f"Top10: {top_10_pass} - Condition: <= {Top10Threshold}")
        elif Top10FilterEnabled and top_10 is None:
            filter_results.append("Top10: Not found in message 🚫")
        else:
            filter_results.append(f"Top10: {top_10 if top_10 else 'Not found'} (Disabled)")

        # Snipers (Pass if <= SnipersThreshold)
        if SniphersFilterEnabled and snipers is not None:
            snipers_pass = snipers <= SnipersThreshold
            filter_results.append(f"Snipers: {snipers} {'✅' if snipers_pass else '🚫'} (Threshold: <= {SnipersThreshold})")
            if not snipers_pass:
                all_filters_pass = False
            logger.info(f"Snipers: {snipers_pass} - Condition: <= {SnipersThreshold}")
        elif SniphersFilterEnabled and snipers is None:
            filter_results.append("Snipers: Not found in message 🚫")
        else:
            filter_results.append(f"Snipers: {snipers if snipers else 'Not found'} (Disabled)")

        # Bundles (Pass if <= BundlesThreshold)
        if BundlesFilterEnabled and bundles is not None:
            bundles_pass = bundles <= BundlesThreshold
            filter_results.append(f"Bundles: {bundles} {'✅' if bundles_pass else '🚫'} (Threshold: <= {BundlesThreshold})")
            if not bundles_pass:
                all_filters_pass = False
            logger.info(f"Bundles: {bundles_pass} - Condition: <= {BundlesThreshold}")
        elif BundlesFilterEnabled and bundles is None:
            filter_results.append("Bundles: Not found in message 🚫")
        else:
            filter_results.append(f"Bundles: {bundles if bundles else 'Not found'} (Disabled)")

        # Insiders (Fail if >= InsidersThreshold)
        if InsidersFilterEnabled and insiders is not None:
            insiders_pass = insiders < InsidersThreshold  # Pass if less than threshold, fail if >=
            filter_results.append(f"Insiders: {insiders} {'✅' if insiders_pass else '🚫'} (Threshold: < {InsidersThreshold})")
            if not insiders_pass:
                all_filters_pass = False
            logger.info(f"Insiders: {insiders_pass} - Condition: < {InsidersThreshold}")
        elif InsidersFilterEnabled and insiders is None:
            filter_results.append("Insiders: Not found in message 🚫")
        else:
            filter_results.append(f"Insiders: {insiders if insiders else 'Not found'} (Disabled)")

        # KOLs (Fail if >= KOLsThreshold)
        if KOLsFilterEnabled and kols is not None:
            kols_pass = kols < KOLsThreshold  # Pass if less than threshold, fail if >=
            filter_results.append(f"KOLs: {kols} {'✅' if kols_pass else '🚫'} (Threshold: < {KOLsThreshold})")
            if not kols_pass:
                all_filters_pass = False
            logger.info(f"KOLs: {kols_pass} - Condition: < {KOLsThreshold}")
        elif KOLsFilterEnabled and kols is None:
            filter_results.append("KOLs: Not found in message 🚫")
        else:
            filter_results.append(f"KOLs: {kols if kols else 'Not found'} (Disabled)")

        # Log to CSV
        log_to_csv(
            ca, bs_ratio, bs_ratio_pass if (CheckHighEnabled or CheckLowEnabled) else None, None,
            dev_sold, dev_sold_left_value, dev_sold_pass,
            top_10, top_10_pass, snipers, snipers_pass,
            bundles, bundles_pass, insiders, insiders_pass,
            kols, kols_pass, all_filters_pass
        )

        # Check if any filters are enabled
        any_filter_enabled = (CheckHighEnabled or CheckLowEnabled or DevSoldFilterEnabled or
                             Top10FilterEnabled or SniphersFilterEnabled or BundlesFilterEnabled or
                             InsidersFilterEnabled or KOLsFilterEnabled)

        # Prepare output
        if not any_filter_enabled:
            output_text = f"No filters are enabled. Please enable at least one filter to evaluate CA.\n{first_line}\n{second_line}"
        elif all_filters_pass:
            filter_summary = "\n".join(filter_results)
            output_text = f"Filter Passed: 🎉\n{filter_summary}\n{first_line}\n{second_line}"
        else:
            filter_summary = "\n".join(filter_results)
            output_text = f"CA did not qualify: 🚫\n{filter_summary}\n{first_line}\n{second_line}"

        entities = []
        if ca:
            ca_match = re.search(r'[A-Za-z0-9]{44}', output_text)
            if ca_match:
                ca = ca_match.group(0)
                text_before_ca = output_text[:output_text.find(ca)]
                ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2
                ca_length = 44
                text_length_utf16 = len(output_text.encode('utf-16-le')) // 2
                if ca_new_offset >= 0 and ca_new_offset + ca_length <= text_length_utf16:
                    entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
                    logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
                else:
                    logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")

        try:
            logger.info("Creating new message for output")
            new_message = await message.answer(output_text, entities=entities)
            logger.info(f"New message ID: {new_message.message_id}")
        except Exception as e:
            logger.error(f"Error creating new message: {e}")
        return

    # Default /button functionality
    if ca and "reflink" in message.text.lower():
        logger.info(f"Adding buttons because 'reflink' found in message: {message.text}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Bloom", url=f"https://t.me/BloomSolana_bot?start=ref_humbleguy_ca_{ca}"),
                InlineKeyboardButton(text="Fasol", url=f"https://t.me/fasol_robot?start=ref_humbleguy_ca_{ca}"),
            ],
            [
                InlineKeyboardButton(text="Maestro", url=f"http://t.me/maestro?start={ca}-beinghumbleguy"),
                InlineKeyboardButton(text="Trojan", url=f"https://t.me/solana_trojanbot?start=r-beinghumbleguy-{ca}")
            ]
        ])
        text = re.sub(r'Forwarded from .*\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Buy token on Fasol Reflink', '', text, flags=re.IGNORECASE)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if ca in line:
                lines[i] = f"🔗 CA: {ca}"
                break
        text = "\n".join(line.strip() for line in lines if line.strip())
        logger.info(f"Final text to send: {text}")

        entities = []
        text_before_ca = text[:text.find(ca)]
        ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2
        logger.info(f"CA position in final text: {text.find(ca)}")
        logger.info(f"Text before CA: {text_before_ca}")
        logger.info(f"Calculated CA UTF-16 offset: {ca_new_offset}")
        if ca_new_offset >= 0:
            ca_length = 44
            text_length_utf16 = len(text.encode('utf-16-le')) // 2
            if ca_new_offset + ca_length <= text_length_utf16:
                entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
                logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
            else:
                logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")

        try:
            logger.info("Attempting to edit the original message")
            edited_message = await message.edit_text(text, reply_markup=keyboard, entities=entities)
            logger.info(f"Successfully edited message ID: {edited_message.message_id}")
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            logger.info("Falling back to posting a new message")
            new_message = await message.answer(text, reply_markup=keyboard, entities=entities)
            logger.info(f"New message ID: {new_message.message_id}")
    else:
        logger.info("No CA found in URL or 'reflink' not present, skipping button addition")
