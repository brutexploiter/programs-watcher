import json
from modules.platforms.functions import find_program, generate_program_key, get_resource, remove_elements, save_data, check_send_notification
from modules.notifier.discord import send_notification


# Checking Bugcrowd
def check_bugcrowd(tmp_dir, mUrl, first_time, db, config):
    json_programs_key = []
    notifications = config['notifications']
    monitor = config['monitor']
    
    # Retrieve Bugcrowd data
    get_resource(tmp_dir, config['url'], "bugcrowd")
    
    with open(f"{tmp_dir}bugcrowd.json") as bugcrowdFile:
        bugcrowd = json.load(bugcrowdFile)

    for program in bugcrowd:
        programName = program.get("name", "Unknown Program")
        programURL = "https://bugcrowd.com" + program.get("briefUrl", "")
        logo = program.get("logoUrl", "")
        data = {
            "programName": programName,
            "reward": {},
            "isRemoved": False,
            "newType": "",
            "newInScope": [],
            "removeInScope": [],
            "newOutOfScope": [],
            "removeOutOfScope": [],
            "programURL": programURL,
            "logo": logo,
            "platformName": "Bugcrowd",
            "isNewProgram": False,
            "color": 14584064
        }
        dataJson = {
            "programName": programName,
            "programURL": programURL,
            "programType": "",
            "outOfScope": [],
            "inScope": [],
            "reward": {}
        }
        
        # Generate program key and find existing program in the database
        programKey = generate_program_key(programName, programURL)
        json_programs_key.append(programKey)
        watcherData = find_program(db, 'bugcrowd', programKey)

        if watcherData is None:
            data["isNewProgram"] = True
            watcherData = {
                "programKey": programKey,
                "programName": programName,
                "programURL": programURL,
                "programType": "",
                "outOfScope": [],
                "inScope": [],
                "reward": {}
            }
        
        # Check target groups
        target_groups = program.get("target_groups", [])
        
        if target_groups is None:  # Handle the case where target_groups might be None
            target_groups = []

        for target in target_groups:
            in_scope = target.get("in_scope", False)
            for item in target.get("targets", []):
                if in_scope:
                    dataJson["inScope"].append(item.get("name"))
                else:
                    dataJson["outOfScope"].append(item.get("name"))

        # Handle rewards
        bounty = {
            "min": "",
            "max": ""
        }
        reward_summary = program.get("rewardSummary")
        if reward_summary:
            dataJson["programType"] = "rdp"
            data["programType"] = "rdp"
            bounty["max"] = reward_summary.get("maxReward", "")
            bounty["min"] = reward_summary.get("minReward", "")
        else:
            dataJson["programType"] = "vdp"
            data["programType"] = "vdp"

        dataJson["reward"] = bounty
        
        # Determine changes
        newInScope = [i for i in dataJson["inScope"] if i not in watcherData["inScope"]]
        removeInScope = [i for i in watcherData["inScope"] if i not in dataJson["inScope"]]
        removedOutOfScope = [i for i in watcherData["outOfScope"] if i not in dataJson["outOfScope"]]
        newOutOfScope = [i for i in dataJson["outOfScope"] if i not in watcherData["outOfScope"]]
        
        hasChanged = False
        is_update = False
        
        # Process in-scope changes
        if newInScope:
            watcherData["inScope"].extend(newInScope)
            notifi_status = notifications['new_inscope']
            hasChanged = True
            if notifi_status:
                data["newInScope"] = newInScope
                is_update = True
                
        if removeInScope:
            remove_elements(watcherData["inScope"], removeInScope)
            hasChanged = True
            notifi_status = notifications['removed_inscope']
            if notifi_status:
                data["removeInScope"] = removeInScope
                is_update = True
        
        # Process out-of-scope changes
        if newOutOfScope:
            watcherData["outOfScope"].extend(newOutOfScope)
            hasChanged = True
            notifi_status = notifications['new_out_of_scope']
            if notifi_status:
                data["newOutOfScope"] = newOutOfScope
                is_update = True
                
        if removedOutOfScope:
            remove_elements(watcherData["outOfScope"], removedOutOfScope)
            hasChanged = True
            notifi_status = notifications['removed_out_of_scope']
            if notifi_status:
                data["removeOutOfScope"] = removedOutOfScope
                is_update = True
        
        # Check for program type changes
        if dataJson["programType"] != watcherData["programType"]:
            watcherData["programType"] = dataJson["programType"]
            hasChanged = True
            notifi_status = notifications['new_type']
            if notifi_status:
                data["newType"] = dataJson["programType"]
                is_update = True
        
        # Check for reward changes
        if dataJson["reward"] != watcherData["reward"]:
            watcherData["reward"] = bounty
            hasChanged = True
            notifi_status = notifications['new_bounty_table']
            if notifi_status:
                data["reward"] = bounty
                is_update = True
        
        # Save changes and send notifications if needed
        if hasChanged:
            save_data(db, "bugcrowd", programKey, watcherData)
            if check_send_notification(first_time, is_update, data, watcherData, monitor, notifications):
                send_notification(data, mUrl)
    
    # Check for removed programs
    db_programs_key = db['bugcrowd'].distinct("programKey")
    removed_programs_key = set(db_programs_key) - set(json_programs_key)
    
    for program_key in removed_programs_key:
        program = find_program(db, 'bugcrowd', program_key)
        if program:  # Ensure program exists before accessing its fields
            data = {
                "color": 14584064,
                "logo": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTwToiI8YA0eLclDkd-vJ0xXs7bun5LdHfTrgJucvI&s",
                "platformName": "Bugcrowd",
                "isRemoved": True, 
                "programName": program.get("programName", "Unknown Program"),
                "programType": program.get("programType", "")
            }
            if notifications['removed_program'] and not first_time:
                send_notification(data, mUrl)
            db['bugcrowd'].delete_many({"programKey": program_key})
