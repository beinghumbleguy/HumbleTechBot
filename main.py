async def process_filter(message: types.Message, text: str, ca: str):
    logger.info("Processing Filter function")
    logger.info(f"Full text received: {repr(text)}")  # Debug: Log the full text with repr
    # Normalize and split lines
    lines = [line.strip() for line in text.replace('\r\n', '\n').split('\n') if line.strip()]
    logger.info(f"Split lines: {lines}")  # Debug: Log all processed lines
    # Extract BuyPercent and SellPercent from Sum line
    buy_percent = None
    sell_percent = None
    for line in lines:
        logger.info(f"Checking line: '{line}'")  # Debug: Log each line
        if "├Sum 🅑:" in line and "Sum 🅢:" in line:
            match = re.search(r'├Sum 🅑:(\d+\.?\d*)%\s*\|\s*Sum 🅢:(\d+\.?\d*)%', line)
            if match:
                buy_percent = float(match.group(1))
                sell_percent = float(match.group(2))
                logger.info(f"Extracted BuyPercent: {buy_percent}, SellPercent: {sell_percent}")
                break
            else:
                logger.warning(f"No match for regex on line: '{line}'")  # Debug: Log if regex fails

    # Extract emoji-based data as fallback
    hold_count = None
    sold_part_count = None
    sold_count = None
    if buy_percent is None or sell_percent is None:
        logger.info("No Sum data found, checking for emoji data")  # Debug: Indicate fallback
        for line in lines:
            logger.info(f"Emoji check on line: '{line}'")  # Debug: Log each line check
            match = re.search(r'└🔴\s*Hold\s+(\d+)\s*\|\s*🟡\s*Sold\s*part\s+(\d+)\s*\|\s*🟢\s*Sold\s+(\d+)', line)
            if match:
                hold_count = int(match.group(1))
                sold_part_count = int(match.group(2))
                sold_count = int(match.group(3))
                logger.info(f"Extracted emoji data: Hold {hold_count}, Sold part {sold_part_count}, Sold {sold_count}")
                break
            else:
                logger.debug(f"No emoji match for line: '{line}'")  # Debug: Log if emoji regex fails

    # Calculate BSRatio
    if buy_percent is not None and sell_percent is not None and sell_percent != 0:
        bs_ratio = buy_percent / sell_percent
        logger.info(f"Calculated BSRatio from Sum: {bs_ratio}")
    elif hold_count is not None and sold_part_count is not None and sold_count is not None:
        total_sold = sold_count + sold_part_count  # Total percentage sold
        remaining = hold_count  # Percentage holding
        if total_sold != 0:
            bs_ratio = (100 - total_sold) / total_sold  # Pseudo-BSRatio: remaining / sold
            logger.info(f"Calculated pseudo-BSRatio from emoji data: {bs_ratio}")
        else:
            bs_ratio = float('inf')  # Avoid division by zero, assume high ratio
            logger.info("Total sold is 0, setting pseudo-BSRatio to infinity")
    else:
        logger.info("No valid Buy/Sell or emoji data found, doing nothing")
        return

    # Get the chat-specific SETUP_VAL, default to 1.0 if not set
    chat_id = str(message.chat.id)
    setup_val = setup_vals.get(chat_id, 1.0)
    logger.info(f"Using SETUP_VAL for chat {chat_id}: {setup_val}")

    # Compare BSRatio with SetupVal
    if bs_ratio >= setup_val:
        logger.info(f"BSRatio ({bs_ratio}) >= SetupVal ({setup_val}), preparing Filter output")
        # Get the first two lines of the original message
        lines = [line.strip() for line in text.replace('\r\n', '\n').split('\n') if line.strip()]
        first_line = "Filter Passed"
        second_line = lines[1].strip() if len(lines) > 1 else ""  # Handle cases with fewer than 2 lines
        # Prepare the output text
        output_text = f"{first_line}\n{second_line}\nCA: {ca}"
        logger.info(f"Filter output text: {output_text}")

        # Apply code entity to the CA
        entities = []
        text_before_ca = f"{first_line}\n{second_line}\nCA: "
        ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2  # UTF-16 offset
        logger.info(f"CA position in final text: {len(text_before_ca)}")
        logger.info(f"Text before CA: {text_before_ca}")
        logger.info(f"Calculated CA UTF-16 offset: {ca_new_offset}")
        if ca_new_offset >= 0:
            ca_length = 44
            text_length_utf16 = len(output_text.encode('utf-16-le')) // 2
            if ca_new_offset + ca_length <= text_length_utf16:
                entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
                logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
            else:
                logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")

        try:
            logger.info("Creating new message for Filter output")
            await message.answer(output_text, entities=entities)
            logger.info("Successfully created new message for Filter")
        except Exception as e:
            logger.error(f"Error creating new message for Filter: {e}")
    else:
        logger.info(f"BSRatio ({bs_ratio}) < SetupVal ({setup_val}), doing nothing")
