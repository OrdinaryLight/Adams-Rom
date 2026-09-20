AdamsRomStartingArea_MapScripts::
# 2 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	map_script MAP_SCRIPT_ON_TRANSITION, AdamsRomStartingArea_MapScripts_MAP_SCRIPT_ON_TRANSITION
	.byte 0

AdamsRomStartingArea_MapScripts_MAP_SCRIPT_ON_TRANSITION:
# 3 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	setrespawn HEAL_LOCATION_ADAMS_ROM_STARTING_AREA
	return


AdamsRomStartingArea_EventScript_Truck::
# 10 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	setvar VAR_0x8005, 10
# 11 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	bufferstring STR_VAR_1, AdamsRomStartingArea_Text_Truck
# 12 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	call AdamsRomStartingArea_EventScript_PayForBarrier
	end


AdamsRomStartingArea_EventScript_WoodenGate::
# 17 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	setvar VAR_0x8005, 50
# 18 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	bufferstring STR_VAR_1, AdamsRomStartingArea_Text_WoodenGate
# 19 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	call AdamsRomStartingArea_EventScript_PayForBarrier
	end


AdamsRomStartingArea_EventScript_StoneBarricade::
# 24 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	setvar VAR_0x8005, 100
# 25 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	bufferstring STR_VAR_1, AdamsRomStartingArea_Text_StoneBarricade
# 26 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	call AdamsRomStartingArea_EventScript_PayForBarrier
	end


AdamsRomStartingArea_EventScript_ObsidianBarricade::
# 31 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	setvar VAR_0x8005, 200
# 32 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	bufferstring STR_VAR_1, AdamsRomStartingArea_Text_ObsidianBarricade
# 33 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	call AdamsRomStartingArea_EventScript_PayForBarrier
	end


AdamsRomStartingArea_EventScript_CrystalBarricade::
# 38 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	setvar VAR_0x8005, 500
# 39 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	bufferstring STR_VAR_1, AdamsRomStartingArea_Text_CrystalBarricade
# 40 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	call AdamsRomStartingArea_EventScript_PayForBarrier
	end


AdamsRomStartingArea_EventScript_PayForBarrier::
# 45 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	lock
# 46 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	buffernumberstring STR_VAR_2, VAR_0x8005
# 47 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	msgbox AdamsRomStartingArea_EventScript_PayForBarrier_Text_0, MSGBOX_YESNO
# 49 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	compare VAR_RESULT, YES
	goto_if_eq AdamsRomStartingArea_EventScript_PayForBarrier_2
AdamsRomStartingArea_EventScript_PayForBarrier_1:
# 62 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	release
	return

AdamsRomStartingArea_EventScript_PayForBarrier_2:
# 50 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	specialvar VAR_RESULT, IsEnoughForCostInVar0x8005
# 52 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	compare VAR_RESULT, TRUE
	goto_if_eq AdamsRomStartingArea_EventScript_PayForBarrier_4
# 58 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	msgbox AdamsRomStartingArea_EventScript_PayForBarrier_Text_2
	goto AdamsRomStartingArea_EventScript_PayForBarrier_1

AdamsRomStartingArea_EventScript_PayForBarrier_4:
# 53 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	special SubtractMoneyFromVar0x8005
# 55 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	special RemoveBarrierPartsBySharedFlag
# 56 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	msgbox AdamsRomStartingArea_EventScript_PayForBarrier_Text_1
	goto AdamsRomStartingArea_EventScript_PayForBarrier_1


AdamsRomStartingArea_EventScript_PayForBarrier_Text_0:
# 47 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	.string "Remove the {STR_VAR_1}?\nCost: ¥{STR_VAR_2}.$"

AdamsRomStartingArea_EventScript_PayForBarrier_Text_1:
# 56 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	.string "The {STR_VAR_1} was removed!$"

AdamsRomStartingArea_EventScript_PayForBarrier_Text_2:
# 58 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	.string "You don't have enough money.$"

AdamsRomStartingArea_Text_WoodenGate::
# 66 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	.string "wooden gate$"

AdamsRomStartingArea_Text_StoneBarricade::
# 70 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	.string "stone barricade$"

AdamsRomStartingArea_Text_ObsidianBarricade::
# 74 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	.string "obsidian barricade$"

AdamsRomStartingArea_Text_CrystalBarricade::
# 78 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	.string "crystal barricade$"

AdamsRomStartingArea_Text_Truck::
# 83 "data\\maps\\AdamsRomStartingArea\\scripts.pory"
	.string "truck$"
