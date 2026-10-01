		OBSLOPElevCurve_25 = LOP_Plot.getCurve(OBS25LOPElev)
		OBSLOPElevCurve_25.setLineWidth(6)
		OBSLOPElevCurve_25 = LOP_Plot.readCurve(OBS25LOPElev)
		OBSLOPElevCurve_25.setLineColor("yellow")
		OBSLOPElevCurve_25.setLineStyle("solid")
		OBSLOPElevCurve_25.setLineWidth(3)

		OBSLOPElevCurve_50 = LOP_Plot.readCurve(OBSLOPElev)
		OBSLOPElevCurve_50.setLineWidth(6)
		OBSLOPElevCurve_50 = LOP_Plot.readCurve(OBSLOPElev)
		OBSLOPElevCurve_50.setLineColor("green")
		OBSLOPElevCurve_50.setLineStyle("solid")
		OBSLOPElevCurve_50.setLineWidth(3)

		OBSLOPElevCurve_75 = LOP_Plot.readCurve(OBS75LOPElev)
		OBSLOPElevCurve_75.setLineWidth(3)
		OBSLOPElevCurve_75 = LOP_Plot.readCurve(OBS75LOPElev)
		OBSLOPElevCurve_75.setLineColor("cyan")
		OBSLOPElevCurve_75.setLineStyle("Solid")
		OBSLOPElevCurve_75.setLineWidth(3)
		
		LOPRuleCurveNormal = LOP_Plot.readCurve(LOPRuleCurveN)
		LOPRuleCurveNormal.setLineWidth(3)
		LOPRuleCurveNormal = LOP_Plot.readCurve(LOPRuleCurveN)
		LOPRuleCurveNormal.setLineColor("Black")
		LOPRuleCurveNormal.setLineStyle("Solid")
		LOPRuleCurveNormal.setLineWidth(3)

		OBSLOPOUTFLOWCurve_50 = LOP_Plot.readCurve(SimLOPOutflow)
		OBSLOPOUTFLOWCurve_50.setLineWidth(3)
		OBSLOPOUTFLOWCurve_50 = LOP_Plot.readCurve(SimLOPOutflow)
		OBSLOPOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSLOPOUTFLOWCurve_50.setLineStyle("dash")
		OBSLOPOUTFLOWCurve_50.setLineWidth(3)


		LOPRuleCurveEIS = LOP_Plot.readCurve(LOPRuleCurve)
		LOPRuleCurveEIS.setLineWidth(3)
		LOPRuleCurveEIS = LOP_Plot.readCurve(LOPRuleCurve)
		LOPRuleCurveEIS.setLineColor("black")
		LOPRuleCurveEIS.setLineStyle("dash")

		OBSLOPINFLOWCurve_50 = LOP_Plot.readCurve(SimLOPInflow)
		OBSLOPINFLOWCurve_50.setLineWidth(3)
		OBSLOPINFLOWCurve_50 = LOP_Plot.readCurve(SimLOPInflow)
		OBSLOPINFLOWCurve_50.setLineColor("green")
		OBSLOPINFLOWCurve_50.setLineStyle("solid")
		OBSLOPINFLOWCurve_50.setLineWidth(3)
		

		
		LOPLBElev2 = LOP_Plot.readCurve(LOPLBElev)
		LOPLBElev2.setLineWidth(5)
		LOPLBElev2 = LOP_Plot.readCurve(LOPLBElev)
		LOPLBElev2.setLineColor("darkmagenta")
		LOPLBElev2.setLineStyle("solid")
        

		############### HCR below

		OBSHCRElevCurve_25 = HCR_Plot.readCurve(OBS25HCRElev)
		OBSHCRElevCurve_25.setLineWidth(6)
		OBSHCRElevCurve_25 = HCR_Plot.readCurve(OBS25HCRElev)
		OBSHCRElevCurve_25.setLineColor("yellow")
		OBSHCRElevCurve_25.setLineStyle("solid")
		OBSHCRElevCurve_25.setLineWidth(3)

		OBSHCRElevCurve_50 = HCR_Plot.readCurve(OBSHCRElev)
		OBSHCRElevCurve_50.setLineWidth(6)
		OBSHCRElevCurve_50 = HCR_Plot.readCurve(OBSHCRElev)
		OBSHCRElevCurve_50.setLineColor("green")
		OBSHCRElevCurve_50.setLineStyle("solid")
		OBSHCRElevCurve_50.setLineWidth(3)

		OBSHCRElevCurve_75 = HCR_Plot.readCurve(OBS75HCRElev)
		OBSHCRElevCurve_75.setLineWidth(3)
		OBSHCRElevCurve_75 = HCR_Plot.readCurve(OBS75HCRElev)
		OBSHCRElevCurve_75.setLineColor("cyan")
		OBSHCRElevCurve_75.setLineStyle("Solid")
		OBSHCRElevCurve_75.setLineWidth(3)
		
		HCRRuleCurveNormal = HCR_Plot.readCurve(HCRRuleCurveN)
		HCRRuleCurveNormal.setLineWidth(3)
		HCRRuleCurveNormal = HCR_Plot.readCurve(HCRRuleCurveN)
		HCRRuleCurveNormal.setLineColor("Black")
		HCRRuleCurveNormal.setLineStyle("Solid")
		HCRRuleCurveNormal.setLineWidth(3)
		
		OBSHCROUTFLOWCurve_50 = HCR_Plot.readCurve(SimHCROutflow)
		OBSHCROUTFLOWCurve_50.setLineWidth(3)
		OBSHCROUTFLOWCurve_50 = HCR_Plot.readCurve(SimHCROutflow)
		OBSHCROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSHCROUTFLOWCurve_50.setLineStyle("dash")
		OBSHCROUTFLOWCurve_50.setLineWidth(3)

		HCRRuleCurveEIS = HCR_Plot.readCurve(HCRRuleCurve)
		HCRRuleCurveEIS.setLineWidth(6)
		HCRRuleCurveEIS = HCR_Plot.readCurve(HCRRuleCurve)
		HCRRuleCurveEIS.setLineColor("black")
		HCRRuleCurveEIS.setLineStyle("dash")
		

		OBSHCRINFLOWCurve_50 = HCR_Plot.readCurve(SimHCRInflow)
		OBSHCRINFLOWCurve_50.setLineWidth(3)
		OBSHCRINFLOWCurve_50 = HCR_Plot.readCurve(SimHCRInflow)
		OBSHCRINFLOWCurve_50.setLineColor("green")
		OBSHCRINFLOWCurve_50.setLineStyle("solid")
		OBSHCRINFLOWCurve_50.setLineWidth(3)
		

		HCRLBElev2 = HCR_Plot.readCurve(HCRLBElev)
		HCRLBElev2.setLineWidth(5)
		HCRLBElev2 = HCR_Plot.readCurve(HCRLBElev)
		HCRLBElev2.setLineColor("darkmagenta")
		HCRLBElev2.setLineStyle("solid")
		HCRLBElev2.setLineWidth(5)

		

		
		
						############### FAL below
		
		OBSFALElevCurve_25 = FAL_Plot.readCurve(OBS25FALElev)
		OBSFALElevCurve_25.setLineWidth(6)
		OBSFALElevCurve_25 = FAL_Plot.readCurve(OBS25FALElev)
		OBSFALElevCurve_25.setLineColor("yellow")
		OBSFALElevCurve_25.setLineStyle("solid")
		OBSFALElevCurve_25.setLineWidth(3)

		OBSFALElevCurve_50 = FAL_Plot.readCurve(OBSFALElev)
		OBSFALElevCurve_50.setLineWidth(6)
		OBSFALElevCurve_50 = FAL_Plot.readCurve(OBSFALElev)
		OBSFALElevCurve_50.setLineColor("green")
		OBSFALElevCurve_50.setLineStyle("solid")
		OBSFALElevCurve_50.setLineWidth(3)

		OBSFALElevCurve_75 = FAL_Plot.readCurve(OBS75FALElev)
		OBSFALElevCurve_75.setLineWidth(3)
		OBSFALElevCurve_75 = FAL_Plot.readCurve(OBS75FALElev)
		OBSFALElevCurve_75.setLineColor("cyan")
		OBSFALElevCurve_75.setLineStyle("Solid")
		OBSFALElevCurve_75.setLineWidth(3)
		
		FALRuleCurveNormal = FAL_Plot.readCurve(FALRuleCurveN)
		FALRuleCurveNormal.setLineWidth(3)
		FALRuleCurveNormal = FAL_Plot.readCurve(FALRuleCurveN)
		FALRuleCurveNormal.setLineColor("black")
		FALRuleCurveNormal.setLineStyle("Solid")
		FALRuleCurveNormal.setLineWidth(3)
		

		OBSFALOUTFLOWCurve_50 = FAL_Plot.readCurve(SimFALOutflow)
		OBSFALOUTFLOWCurve_50.setLineWidth(3)
		OBSFALOUTFLOWCurve_50 = FAL_Plot.readCurve(SimFALOutflow)
		OBSFALOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSFALOUTFLOWCurve_50.setLineStyle("dash")
		OBSFALOUTFLOWCurve_50.setLineWidth(3)


		FALRuleCurveEIS = FAL_Plot.readCurve(FALRuleCurve)
		FALRuleCurveEIS.setLineWidth(6)
		FALRuleCurveEIS = FAL_Plot.readCurve(FALRuleCurve)
		FALRuleCurveEIS.setLineColor("black")
		FALRuleCurveEIS.setLineStyle("dash")
		FALRuleCurveEIS.setLineWidth(3)
		

		OBSFALINFLOWCurve_50 = FAL_Plot.readCurve(SimFALInflow)
		OBSFALINFLOWCurve_50.setLineWidth(3)
		OBSFALINFLOWCurve_50 = FAL_Plot.readCurve(SimFALInflow)
		OBSFALINFLOWCurve_50.setLineColor("green")
		OBSFALINFLOWCurve_50.setLineStyle("solid")
		OBSFALINFLOWCurve_50.setLineWidth(3)
		

		
		FALLBElev2 = FAL_Plot.readCurve(FALLBElev)
		FALLBElev2.setLineWidth(5)
		FALLBElev2 = FAL_Plot.readCurve(FALLBElev)
		FALLBElev2.setLineColor("darkmagenta")
		FALLBElev2.setLineStyle("solid")
		FALLBElev2.setLineWidth(5)
		

		
		
						############### CGR below
		OBSCGRElevCurve_25 = CGR_Plot.readCurve(OBS25CGRElev)
		OBSCGRElevCurve_25.setLineWidth(6)
		OBSCGRElevCurve_25 = CGR_Plot.readCurve(OBS25CGRElev)
		OBSCGRElevCurve_25.setLineColor("yellow")
		OBSCGRElevCurve_25.setLineStyle("solid")
		OBSCGRElevCurve_25.setLineWidth(3)
		
		OBSCGRElevCurve_50 = CGR_Plot.readCurve(OBSCGRElev)
		OBSCGRElevCurve_50.setLineWidth(6)
		OBSCGRElevCurve_50 = CGR_Plot.readCurve(OBSCGRElev)
		OBSCGRElevCurve_50.setLineColor("green")
		OBSCGRElevCurve_50.setLineStyle("solid")
		OBSCGRElevCurve_50.setLineWidth(3)

		OBSCGRElevCurve_75 = CGR_Plot.readCurve(OBS75CGRElev)
		OBSCGRElevCurve_75.setLineWidth(3)
		OBSCGRElevCurve_75 = CGR_Plot.readCurve(OBS75CGRElev)
		OBSCGRElevCurve_75.setLineColor("cyan")
		OBSCGRElevCurve_75.setLineStyle("Solid")
		OBSCGRElevCurve_75.setLineWidth(3)
		
		CGRRuleCurveNormal = CGR_Plot.readCurve(CGRRuleCurveN)
		CGRRuleCurveNormal.setLineWidth(5)
		CGRRuleCurveNormal = CGR_Plot.readCurve(CGRRuleCurveN)
		CGRRuleCurveNormal.setLineColor("Black")
		CGRRuleCurveNormal.setLineStyle("Solid")
		CGRRuleCurveNormal.setLineWidth(5)


		OBSCGROUTFLOWCurve_50 = CGR_Plot.readCurve(SimCGROutflow)
		OBSCGROUTFLOWCurve_50.setLineWidth(3)
		OBSCGROUTFLOWCurve_50 = CGR_Plot.readCurve(SimCGROutflow)
		OBSCGROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSCGROUTFLOWCurve_50.setLineStyle("dash")
		OBSCGROUTFLOWCurve_50.setLineWidth(3)

		CGRRuleCurveEIS = CGR_Plot.readCurve(CGRRuleCurve)
		CGRRuleCurveEIS.setLineWidth(3)
		CGRRuleCurveEIS = CGR_Plot.readCurve(CGRRuleCurve)
		CGRRuleCurveEIS.setLineColor("black")
		CGRRuleCurveEIS.setLineStyle("dash")
		

		OBSCGRINFLOWCurve_50 = CGR_Plot.readCurve(SimCGRInflow)
		OBSCGRINFLOWCurve_50.setLineWidth(3)
		OBSCGRINFLOWCurve_50 = CGR_Plot.readCurve(SimCGRInflow)
		OBSCGRINFLOWCurve_50.setLineColor("green")
		OBSCGRINFLOWCurve_50.setLineStyle("solid")
		
		CGRLBElev2 = CGR_Plot.readCurve(CGRLBElev)
		CGRLBElev2.setLineWidth(5)
		CGRLBElev2 = CGR_Plot.readCurve(CGRLBElev)
		CGRLBElev2.setLineColor("darkmagenta")
		CGRLBElev2.setLineStyle("solid")
		
		
				############### BLR below
		
		OBSBLRElevCurve_25 = BLR_Plot.readCurve(OBS25BLRElev)
		OBSBLRElevCurve_25.setLineWidth(6)
		OBSBLRElevCurve_25 = BLR_Plot.readCurve(OBS25BLRElev)
		OBSBLRElevCurve_25.setLineColor("yellow")
		OBSBLRElevCurve_25.setLineStyle("solid")
		OBSBLRElevCurve_25.setLineWidth(3)

		OBSBLRElevCurve_50 = BLR_Plot.readCurve(OBSBLRElev)
		OBSBLRElevCurve_50.setLineWidth(6)
		OBSBLRElevCurve_50 = BLR_Plot.readCurve(OBSBLRElev)
		OBSBLRElevCurve_50.setLineColor("green")
		OBSBLRElevCurve_50.setLineStyle("solid")
		OBSBLRElevCurve_50.setLineWidth(3)

		OBSBLRElevCurve_75 = BLR_Plot.readCurve(OBS75BLRElev)
		OBSBLRElevCurve_75.setLineWidth(3)
		OBSBLRElevCurve_75 = BLR_Plot.readCurve(OBS75BLRElev)
		OBSBLRElevCurve_75.setLineColor("cyan")
		OBSBLRElevCurve_75.setLineStyle("Solid")
		OBSBLRElevCurve_75.setLineWidth(3)
		
		BLRRuleCurveNormal = BLR_Plot.readCurve(BLRRuleCurveN)
		BLRRuleCurveNormal.setLineWidth(3)
		BLRRuleCurveNormal = BLR_Plot.readCurve(BLRRuleCurveN)
		BLRRuleCurveNormal.setLineColor("black")
		BLRRuleCurveNormal.setLineStyle("Solid")
		BLRRuleCurveNormal.setLineWidth(3)


		OBSBLROUTFLOWCurve_50 = BLR_Plot.readCurve(SimBLROutflow)
		OBSBLROUTFLOWCurve_50.setLineWidth(3)
		OBSBLROUTFLOWCurve_50 = BLR_Plot.readCurve(SimBLROutflow)
		OBSBLROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSBLROUTFLOWCurve_50.setLineStyle("dash")
		OBSBLROUTFLOWCurve_50.setLineWidth(3)

		
		BLRRuleCurveEIS = BLR_Plot.readCurve(BLRRuleCurve)
		BLRRuleCurveEIS.setLineWidth(6)
		BLRRuleCurveEIS = BLR_Plot.readCurve(BLRRuleCurve)
		BLRRuleCurveEIS.setLineColor("black")
		BLRRuleCurveEIS.setLineStyle("dash")
		BLRRuleCurveEIS.setLineWidth(3)
		
		OBSBLRINFLOWCurve_50 = BLR_Plot.readCurve(SimBLRInflow)
		OBSBLRINFLOWCurve_50.setLineWidth(3)
		OBSBLRINFLOWCurve_50 = BLR_Plot.readCurve(SimBLRInflow)
		OBSBLRINFLOWCurve_50.setLineColor("green")
		OBSBLRINFLOWCurve_50.setLineStyle("solid")
		OBSBLRINFLOWCurve_50.setLineWidth(3)
		

		BLRLBELEV2 = BLR_Plot.readCurve(BLRLBElev)
		BLRLBELEV2.setLineWidth(3)
		BLRLBELEV2.setLineColor("darkmagenta")
		BLRLBELEV2.setLineStyle("solid")
		
				############### DOR below
		OBSDORElevCurve_25 = DOR_Plot.readCurve(OBS25DORElev)
		OBSDORElevCurve_25.setLineWidth(6)
		OBSDORElevCurve_25 = DOR_Plot.readCurve(OBS25DORElev)
		OBSDORElevCurve_25.setLineColor("yellow")
		OBSDORElevCurve_25.setLineStyle("solid")
		OBSDORElevCurve_25.setLineWidth(3)

		OBSDORElevCurve_50 = DOR_Plot.readCurve(OBSDORElev)
		OBSDORElevCurve_50.setLineWidth(6)
		OBSDORElevCurve_50 = DOR_Plot.readCurve(OBSDORElev)
		OBSDORElevCurve_50.setLineColor("green")
		OBSDORElevCurve_50.setLineStyle("solid")
		OBSDORElevCurve_50.setLineWidth(3)

		OBSDORElevCurve_75 = DOR_Plot.readCurve(OBS75DORElev)
		OBSDORElevCurve_75.setLineWidth(3)
		OBSDORElevCurve_75 = DOR_Plot.readCurve(OBS75DORElev)
		OBSDORElevCurve_75.setLineColor("cyan")
		OBSDORElevCurve_75.setLineStyle("Solid")
		OBSDORElevCurve_75.setLineWidth(3)
		
		DORRuleCurveNormal = DOR_Plot.readCurve(DORRuleCurveN)
		DORRuleCurveNormal.setLineWidth(3)
		DORRuleCurveNormal = DOR_Plot.readCurve(DORRuleCurveN)
		DORRuleCurveNormal.setLineColor("black")
		DORRuleCurveNormal.setLineStyle("Solid")
		DORRuleCurveNormal.setLineWidth(3)
		

		OBSDOROUTFLOWCurve_50 = DOR_Plot.readCurve(SimDOROutflow)
		OBSDOROUTFLOWCurve_50.setLineWidth(3)
		OBSDOROUTFLOWCurve_50 = DOR_Plot.readCurve(SimDOROutflow)
		OBSDOROUTFLOWCurve_50.setLineColor("darkgreen")
		OBSDOROUTFLOWCurve_50.setLineStyle("dash")
		OBSDOROUTFLOWCurve_50.setLineWidth(3)

		
		DORRuleCurveEIS = DOR_Plot.readCurve(DORRuleCurve)
		DORRuleCurveEIS.setLineWidth(6)
		DORRuleCurveEIS = DOR_Plot.readCurve(DORRuleCurve)
		DORRuleCurveEIS.setLineColor("black")
		DORRuleCurveEIS.setLineStyle("dash")
		DORRuleCurveEIS.setLineWidth(3)
		

		OBSDORINFLOWCurve_50 = DOR_Plot.readCurve(SimDORInflow)
		OBSDORINFLOWCurve_50.setLineWidth(3)
		OBSDORINFLOWCurve_50 = DOR_Plot.readCurve(SimDORInflow)
		OBSDORINFLOWCurve_50.setLineColor("green")
		OBSDORINFLOWCurve_50.setLineStyle("solid")
		OBSDORINFLOWCurve_50.setLineWidth(3)
		

		DORLBElev2 = DOR_Plot.readCurve(DORLBElev)
		DORLBElev2.setLineWidth(5)
		DORLBElev2.setLineColor("darkmagenta")
		DORLBElev2.setLineStyle("solid")
	
						############### COT below
		OBSCOTElevCurve_25 = COT_Plot.readCurve(OBS25COTElev)
		OBSCOTElevCurve_25.setLineWidth(6)
		OBSCOTElevCurve_25 = COT_Plot.readCurve(OBS25COTElev)
		OBSCOTElevCurve_25.setLineColor("yellow")
		OBSCOTElevCurve_25.setLineStyle("solid")
		OBSCOTElevCurve_25.setLineWidth(3)

		OBSCOTElevCurve_50 = COT_Plot.readCurve(OBSCOTElev)
		OBSCOTElevCurve_50.setLineWidth(6)
		OBSCOTElevCurve_50 = COT_Plot.readCurve(OBSCOTElev)
		OBSCOTElevCurve_50.setLineColor("green")
		OBSCOTElevCurve_50.setLineStyle("solid")
		OBSCOTElevCurve_50.setLineWidth(3)

		OBSCOTElevCurve_75 = COT_Plot.readCurve(OBS75COTElev)
		OBSCOTElevCurve_75.setLineWidth(3)
		OBSCOTElevCurve_75 = COT_Plot.readCurve(OBS75COTElev)
		OBSCOTElevCurve_75.setLineColor("cyan")
		OBSCOTElevCurve_75.setLineWidth(3)
		
		COTRuleCurveNormal = COT_Plot.readCurve(COTRuleCurveN)
		OBSCOTElevCurve_75.setLineWidth(3)
		OBSCOTElevCurve_75 = COT_Plot.readCurve(COTRuleCurveN)
		OBSCOTElevCurve_75.setLineColor("Black")
		OBSCOTElevCurve_75.setLineStyle("Solid")
		OBSCOTElevCurve_75.setLineWidth(3)
		

		OBSCOTOUTFLOWCurve_50 = COT_Plot.readCurve(SimCOTOutflow)
		OBSCOTOUTFLOWCurve_50.setLineWidth(3)
		OBSCOTOUTFLOWCurve_50 = COT_Plot.readCurve(SimCOTOutflow)
		OBSCOTOUTFLOWCurve_50.setLineColor("darkgreen")
		OBSCOTOUTFLOWCurve_50.setLineStyle("dash")
		OBSCOTOUTFLOWCurve_50.setLineWidth(3)

		
		COTRuleCurveEIS = COT_Plot.readCurve(COTRuleCurve)
		COTRuleCurveEIS.setLineWidth(3)
		COTRuleCurveEIS = COT_Plot.readCurve(COTRuleCurve)
		COTRuleCurveEIS.setLineColor("black")
		COTRuleCurveEIS.setLineStyle("dash")
		COTRuleCurveEIS.setLineWidth(3)
		
		OBSCOTINFLOWCurve_50 = COT_Plot.readCurve(SimCOTInflow)
		OBSCOTINFLOWCurve_50.setLineWidth(3)
		OBSCOTINFLOWCurve_50.setLineColor("green")
		OBSCOTINFLOWCurve_50.setLineStyle("solid")
	

		OCOTLBELEV2 = COT_Plot.readCurve(COTLBElev)
		OCOTLBELEV2.setLineWidth(3)
		OCOTLBELEV2.setLineColor("darkmagenta")
		OCOTLBELEV2.setLineStyle("solid")

        
		##### Albany below


		
		ALBOFlow_50 = ALBO_Plot.readCurve(ALBOFlow)
		ALBOFlow_50.setLineWidth(3)
		ALBOFlow_50 = ALBO_Plot.readCurve(ALBOFlow)
		ALBOFlow_50.setLineColor("green")
		ALBOFlow_50.setLineStyle("solid")
		ALBOFlow_50.setLineWidth(3)

		ALBOFlow_75 = ALBO_Plot.readCurve(ALBO75Flow)
		ALBOFlow_75.setLineWidth(3)
		ALBOFlow_75 = ALBO_Plot.readCurve(ALBO75Flow)
		ALBOFlow_75.setLineColor("cyan")
		ALBOFlow_75.setLineStyle("solid")
		ALBOFlow_75.setLineWidth(3)
		
		ALBOFlow_25 = ALBO_Plot.readCurve(ALBO25Flow)
		ALBOFlow_25.setLineWidth(3)
		ALBOFlow_25 = ALBO_Plot.readCurve(ALBO25Flow)
		ALBOFlow_25.setLineColor("yellow")
		ALBOFlow_25.setLineStyle("solid")
		ALBOFlow_25.setLineWidth(3)
		######SALEM BELOW


		
		SALEMFlow_50 = SALO_Plot.readCurve(SALOFlow)
		SALEMFlow_50.setLineWidth(3)
		SALEMFlow_50 = SALO_Plot.readCurve(SALOFlow)
		SALEMFlow_50.setLineColor("green")
		SALEMFlow_50.setLineStyle("solid")
		SALEMFlow_50.setLineWidth(3)

		SALEMFlow_75 = SALO_Plot.readCurve(SALO75Flow)
		SALEMFlow_75.setLineWidth(3)
		SALEMFlow_75 = SALO_Plot.readCurve(SALO75Flow)
		SALEMFlow_75.setLineColor("cyan")
		SALEMFlow_75.setLineStyle("solid")
		SALEMFlow_75.setLineWidth(3)
		
		SALEMFlow_25 = SALO_Plot.readCurve(SALO25Flow)
		SALEMFlow_25.setLineWidth(3)
		SALEMFlow_25 = SALO_Plot.readCurve(SALO25Flow)
		SALEMFlow_25.setLineColor("yellow")
		SALEMFlow_25.setLineStyle("solid")
		SALEMFlow_25.setLineWidth(3)
		
		EUGENEFlow_50 = EUGO_Plot.readCurve(EUGOFlow)
		EUGENEFlow_50.setLineWidth(3)
		EUGENEFlow_50 = EUGO_Plot.readCurve(EUGOFlow)
		EUGENEFlow_50.setLineColor("green")
		EUGENEFlow_50.setLineStyle("solid")
		EUGENEFlow_50.setLineWidth(3)

		EUGENEFlow_75 = EUGO_Plot.readCurve(EUGO75Flow)
		EUGENEFlow_75.setLineWidth(3)
		EUGENEFlow_75 = EUGO_Plot.readCurve(EUGO75Flow)
		EUGENEFlow_75.setLineColor("cyan")
		EUGENEFlow_75.setLineStyle("solid")
		EUGENEFlow_75.setLineWidth(3)
		
		EUGENEFlow_25 = EUGO_Plot.readCurve(EUGO25Flow)
		EUGENEFlow_25.setLineWidth(3)
		EUGENEFlow_25 = EUGO_Plot.readCurve(EUGO25Flow)
		EUGENEFlow_25.setLineColor("yellow")
		EUGENEFlow_25.setLineStyle("solid")
		EUGENEFlow_25.setLineWidth(3)
        
		HARRISBURGFlow_50 = HARO_Plot.readCurve(HAROFlow)
		HARRISBURGFlow_50.setLineWidth(3)
		HARRISBURGFlow_50 = HARO_Plot.readCurve(HAROFlow)
		HARRISBURGFlow_50.setLineColor("green")
		HARRISBURGFlow_50.setLineStyle("solid")
		HARRISBURGFlow_50.setLineWidth(3)

		HARRISBURGFlow_75 = HARO_Plot.readCurve(HARO75Flow)
		HARRISBURGFlow_75.setLineWidth(3)
		HARRISBURGFlow_75 = HARO_Plot.readCurve(HARO75Flow)
		HARRISBURGFlow_75.setLineColor("cyan")
		HARRISBURGFlow_75.setLineStyle("solid")
		HARRISBURGFlow_75.setLineWidth(3)
		
		HARRISBURGFlow_25 = HARO_Plot.readCurve(HARO25Flow)
		HARRISBURGFlow_25.setLineWidth(3)
		HARRISBURGFlow_25 = HARO_Plot.readCurve(HARO25Flow)
		HARRISBURGFlow_25.setLineColor("yellow")
		HARRISBURGFlow_25.setLineStyle("solid")
		HARRISBURGFlow_25.setLineWidth(3)        
#####Axis Formating####
		TopViewport_CGR = CGR_Plot.readViewport(0)
		BottomViewport_CGR = CGR_Plot.readViewport(1)
		Top_Y_Axis = TopViewport_CGR.readAxis("Y1")
		Top_Y_AxisLabel = TopViewport_CGR.readAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_CGR.readAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.readProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_CGR.readAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_CGR.readAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_CGR.readAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(250)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.readProperties()
		BottomTicProps.setMajorTicFontStyle(1)
		
		
		CGR_SW = AxisMarker()
		CGR_SW.axis = "Y"
		CGR_SW.value = "1656.75"
		CGR_SW.labelText = "CGR Spillway ~ 1656.75"
		CGR_SW.labelPosition = "above"
		CGR_SW.labelColor = "Purple"
		CGR_SW.labelFont = "Dialog,BOLD,14";
		CGR_SW.lineColor = "Purple"
		CGR_SW.lineStyle = "dot"
		CGR_SW.lineWidth = 4
		TopViewport_CGR.addAxisMarker(CGR_SW)	

		CGR_BR = AxisMarker()
		CGR_BR.axis = "Y"
		CGR_BR.value = "1635.0"
		CGR_BR.labelText = "CGR BoatRamps ~ 1635.0"
		CGR_BR.labelPosition = "above"
		CGR_BR.labelColor = "black"
		CGR_BR.labelFont = "Dialog,BOLD,14";
		CGR_BR.lineColor = "black"
		CGR_BR.lineStyle = "dot"
		CGR_BR.lineWidth = 4
		TopViewport_CGR.addAxisMarker(CGR_BR)		


		
		TopViewport_LOP = LOP_Plot.readViewport(0)
		BottomViewport_LOP = LOP_Plot.readViewport(1)
		Top_Y_Axis = TopViewport_LOP.readAxis("Y1")
		Top_Y_AxisLabel = TopViewport_LOP .readAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_LOP .readAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(14, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.readProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_LOP .readAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_LOP .readAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_LOP .readAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.readProperties()
		BottomTicProps.setMajorTicFontStyle(1)
        
		LOP_SW = AxisMarker()
		LOP_SW.axis = "Y"
		LOP_SW.value = "887.5"
		LOP_SW.labelText = "LOP Spillway ~ 887.5"
		LOP_SW.labelPosition = "above"
		LOP_SW.labelColor = "Purple"
		LOP_SW.labelFont = "Dialog,BOLD,14";
		LOP_SW.lineColor = "purple"
		LOP_SW.lineStyle = "dot"
		LOP_SW.lineWidth = 4
		TopViewport_LOP.addAxisMarker(LOP_SW)
        
		Meridian = AxisMarker()
		Meridian.axis = "Y"
		Meridian.value = "911"
		Meridian.labelText = "Meridian Hampton ~ 911"
		Meridian.labelPosition = "above"
		Meridian.labelColor = "black"
		Meridian.labelFont = "Dialog,BOLD,14";
		Meridian.lineColor = "black"
		Meridian.lineStyle = "dot"
		Meridian.lineWidth = 4
		TopViewport_LOP.addAxisMarker(Meridian)

		Black_Canyon = AxisMarker()
		Black_Canyon.axis = "Y"
		Black_Canyon.value = "900.0"
		Black_Canyon.labelText = "Black_Canyon BR ~ 900"
		Black_Canyon.labelPosition = "above"
		Black_Canyon.labelColor = "black"
		Black_Canyon.labelFont = "Dialog,BOLD,14";
		Black_Canyon.lineColor = "black"
		Black_Canyon.lineStyle = "dot"
		Black_Canyon.lineWidth = 4
		TopViewport_LOP.addAxisMarker(Black_Canyon)        

		Signal_point = AxisMarker()
		Signal_point.axis = "Y"
		Signal_point.value = "821.0"
		Signal_point.labelText = "Signal_point BR ~ 821"
		Signal_point.labelPosition = "below"
		Signal_point.labelColor = "black"
		Signal_point.labelFont = "Dialog,BOLD,14";
		Signal_point.lineColor = "black"
		Signal_point.lineStyle = "dot"
		Signal_point.lineWidth = 4
		TopViewport_LOP.addAxisMarker(Signal_point)       
        
        
		TopViewport_HCR = HCR_Plot.readViewport(0)
		BottomViewport_HCR = HCR_Plot.readViewport(1)
		Top_Y_Axis = TopViewport_HCR.readAxis("Y1")
		Top_Y_AxisLabel = TopViewport_HCR.readAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_HCR.readAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(14, 14, 14, 22)
		TopTicProps = Top_Y_AxisTics.readProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_HCR.readAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_HCR.readAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_HCR.readAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.readProperties()
		BottomTicProps.setMajorTicFontStyle(1)
        
        
        
		HCRSW = AxisMarker()
		HCRSW.axis = "Y"
		HCRSW.value = "1495.5"
		HCRSW.labelText = "HCR Spillway ~ 1495.5"
		HCRSW.labelPosition = "above"
		HCRSW.labelColor = "purple"
		HCRSW.labelFont = "Dialog,BOLD,14";
		HCRSW.lineColor = "purple"
		HCRSW.lineStyle = "dot"
		HCRSW.lineWidth = 4
		TopViewport_HCR.addAxisMarker(HCRSW)

		Bingham_BR = AxisMarker()
		Bingham_BR.axis = "Y"
		Bingham_BR.value = "1520"
		Bingham_BR.labelText = "Bing BR ~ 1520"
		Bingham_BR.labelPosition = "above"
		Bingham_BR.labelColor = "black"
		Bingham_BR.labelFont = "Dialog,BOLD,14";
		Bingham_BR.lineColor = "black"
		Bingham_BR.lineStyle = "dot"
		Bingham_BR.lineWidth = 4
		TopViewport_HCR.addAxisMarker(Bingham_BR)
		
		CTBeach_BR = AxisMarker()
		CTBeach_BR.axis = "Y"
		CTBeach_BR.value = "1507"
		CTBeach_BR.labelText = "CTBeach BR ~ 1507"
		CTBeach_BR.labelPosition = "above"
		CTBeach_BR.labelColor = "black"
		CTBeach_BR.labelFont = "Dialog,BOLD,14";
		CTBeach_BR.lineColor = "black"
		CTBeach_BR.lineStyle = "dot"
		CTBeach_BR.lineWidth = 4
		TopViewport_HCR.addAxisMarker(CTBeach_BR) 

		Packard_BR = AxisMarker()
		Packard_BR.axis = "Y"
		Packard_BR.value = "1441"
		Packard_BR.labelText = "Packard BR ~ 1441"
		Packard_BR.labelPosition = "above"
		Packard_BR.labelColor = "black"
		Packard_BR.labelFont = "Dialog,BOLD,14";
		Packard_BR.lineColor = "black"
		Packard_BR.lineStyle = "dot"
		Packard_BR.lineWidth = 4
		TopViewport_HCR.addAxisMarker(Packard_BR)        
        
        




        
		

		
		TopViewport_FAL = FAL_Plot.readViewport(0)
		BottomViewport_FAL = FAL_Plot.readViewport(1)
		Top_Y_Axis = TopViewport_FAL.readAxis("Y1")
		Top_Y_AxisLabel = TopViewport_FAL.readAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_FAL.readAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.readProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_FAL.readAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_FAL.readAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_FAL.readAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.readProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		FALSW = AxisMarker()
		FALSW.axis = "Y"
		FALSW.value = "791.6"
		FALSW.labelText = "FAL Spillway ~ 791.6"
		FALSW.labelPosition = "above"
		FALSW.labelColor = "purple"
		FALSW.labelFont = "Dialog,BOLD,14";
		FALSW.lineColor = "purple"
		FALSW.lineStyle = "dot"
		FALSW.lineWidth = 4
		TopViewport_FAL.addAxisMarker(FALSW)        
        
        
        
		Cascara_BR = AxisMarker()
		Cascara_BR.axis = "Y"
		Cascara_BR.value = "815"
		Cascara_BR.labelText = "Cascara BR ~ 815"
		Cascara_BR.labelPosition = "above"
		Cascara_BR.labelColor = "black"
		Cascara_BR.labelFont = "Dialog,BOLD,14";
		Cascara_BR.lineColor = "black"
		Cascara_BR.lineStyle = "dot"
		Cascara_BR.lineWidth = 4
		TopViewport_FAL.addAxisMarker(Cascara_BR)    

		Winberry_BR = AxisMarker()
		Winberry_BR.axis = "Y"
		Winberry_BR.value = "803"
		Winberry_BR.labelText = "Winberry BR ~ 803"
		Winberry_BR.labelPosition = "above"
		Winberry_BR.labelColor = "black"
		Winberry_BR.labelFont = "Dialog,BOLD,14";
		Winberry_BR.lineColor = "black"
		Winberry_BR.lineStyle = "dot"
		Winberry_BR.lineWidth = 4
		TopViewport_FAL.addAxisMarker(Winberry_BR)  

		NorthShore_BR = AxisMarker()
		NorthShore_BR.axis = "Y"
		NorthShore_BR.value = "729"
		NorthShore_BR.labelText = "NorthShore BR ~ 729"
		NorthShore_BR.labelPosition = "above"
		NorthShore_BR.labelColor = "black"
		NorthShore_BR.labelFont = "Dialog,BOLD,14";
		NorthShore_BR.lineColor = "black"
		NorthShore_BR.lineStyle = "dot"
		NorthShore_BR.lineWidth = 4
		TopViewport_FAL.addAxisMarker(NorthShore_BR) 

		
		TopViewport_BLR = BLR_Plot.readViewport(0)
		BottomViewport_BLR = BLR_Plot.readViewport(1)
		Top_Y_Axis = TopViewport_BLR.readAxis("Y1")
		Top_Y_AxisLabel = TopViewport_BLR.readAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_BLR.readAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.readProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_BLR.readAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_BLR.readAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_BLR.readAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.readProperties()
		BottomTicProps.setMajorTicFontStyle(1)



		BLRSW = AxisMarker()
		BLRSW.axis = "Y"
		BLRSW.value = "1321"
		BLRSW.labelText = "BLR Spillway ~ 1321"
		BLRSW.labelPosition = "above"
		BLRSW.labelColor = "purple"
		BLRSW.labelFont = "Dialog,BOLD,14";
		BLRSW.lineColor = "purple"
		BLRSW.lineStyle = "dot"
		BLRSW.lineWidth = 4
		TopViewport_BLR.addAxisMarker(BLRSW)        
        
        
		LookOut_BR= AxisMarker()
		LookOut_BR.axis = "Y"
		LookOut_BR.value = "1330"
		LookOut_BR.labelText = "LookOut BR ~ 1330"
		LookOut_BR.labelPosition = "above"
		LookOut_BR.labelColor = "black"
		LookOut_BR.labelFont = "Dialog,BOLD,14";
		LookOut_BR.lineColor = "black"
		LookOut_BR.lineStyle = "dot"
		LookOut_BR.lineWidth = 4
		TopViewport_BLR.addAxisMarker(LookOut_BR)  

		SaddleDam_BR = AxisMarker()
		SaddleDam_BR.axis = "Y"
		SaddleDam_BR.value = "1295"
		SaddleDam_BR.labelText = "SaddleDam BR ~ 1295"
		SaddleDam_BR.labelPosition = "above"
		SaddleDam_BR.labelColor = "black"
		SaddleDam_BR.labelFont = "Dialog,BOLD,14";
		SaddleDam_BR.lineColor = "black"
		SaddleDam_BR.lineStyle = "dot"
		SaddleDam_BR.lineWidth = 4
		TopViewport_BLR.addAxisMarker(SaddleDam_BR)  
		
		TopViewport_DOR = DOR_Plot.readViewport(0)
		BottomViewport_DOR = DOR_Plot.readViewport(1)
		Top_Y_Axis = TopViewport_DOR.readAxis("Y1")
		Top_Y_AxisLabel = TopViewport_DOR.readAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_DOR.readAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.readProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_Axis = BottomViewport_DOR.readAxis("Y1")
		Bottom_Y_AxisLabel = BottomViewport_DOR.readAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_DOR.readAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.readProperties()
		BottomTicProps.setMajorTicFontStyle(1)

        

        
		HarmsPark_BR = AxisMarker()
		HarmsPark_BR.axis = "Y"
		HarmsPark_BR.value = "820"
		HarmsPark_BR.labelText = "HarmsPark BR ~ 820"
		HarmsPark_BR.labelPosition = "above"
		HarmsPark_BR.labelColor = "black"
		HarmsPark_BR.labelFont = "Dialog,BOLD,14";
		HarmsPark_BR.lineColor = "black"
		HarmsPark_BR.lineStyle = "dot"
		HarmsPark_BR.lineWidth = 4
		TopViewport_DOR.addAxisMarker(HarmsPark_BR)  


		BB_BR = AxisMarker()
		BB_BR.axis = "Y"
		BB_BR.value = "765"
		BB_BR.labelText = "Baker Bay BR ~ 765"
		BB_BR.labelPosition = "above"
		BB_BR.labelColor = "black"
		BB_BR.labelFont = "Dialog,BOLD,14";
		BB_BR.lineColor = "black"
		BB_BR.lineStyle = "dot"
		BB_BR.lineWidth = 4
		TopViewport_DOR.addAxisMarker(BB_BR)  
		
	

		
		TopViewport_COT = COT_Plot.readViewport(0)
		BottomViewport_COT = COT_Plot.readViewport(1)
		Top_Y_Axis = TopViewport_COT.readAxis("Y1")
		Top_Y_AxisLabel = TopViewport_COT.readAxisLabel("Y1")
		Top_Y_AxisTics = TopViewport_COT.readAxisTics("Y1")
		Top_Y_Axis.setMajorTicInterval(10)
		Top_Y_Axis.setLabel("Pool Elevation")
		Top_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Top_Y_AxisLabel.setFontStyle("bold")
		Top_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		TopTicProps = Top_Y_AxisTics.readProperties()
		TopTicProps.setMajorTicFontStyle(1)
		Bottom_Y_AxisLabel = BottomViewport_COT.readAxisLabel("Y1")
		Bottom_Y_AxisTics = BottomViewport_COT.readAxisTics("Y1")
		Bottom_Y_Axis.setMajorTicInterval(50)
		Bottom_Y_Axis.setLabel("Outlfow")
		Bottom_Y_AxisLabel.setFontSizes(26, 26, 22, 30)
		Bottom_Y_AxisLabel.setFontStyle("bold")
		Bottom_Y_AxisTics.setFontSizes(18, 18, 14, 22)
		BottomTicProps = Top_Y_AxisTics.readProperties()
		BottomTicProps.setMajorTicFontStyle(1)

		WilsonCreek_BR = AxisMarker()
		WilsonCreek_BR.axis = "Y"
		WilsonCreek_BR.value = "779"
		WilsonCreek_BR.labelText = "Wilson Creek BR ~ 779"
		WilsonCreek_BR.labelPosition = "above"
		WilsonCreek_BR.labelColor = "black"
		WilsonCreek_BR.labelFont = "Dialog,BOLD,14";
		WilsonCreek_BR.lineColor = "black"
		WilsonCreek_BR.lineStyle = "dot"
		WilsonCreek_BR.lineWidth = 4
		TopViewport_COT.addAxisMarker(WilsonCreek_BR)
        
		start = HecTime()
		start.set(forecast_time)
		CurrentTime = AxisMarker()
		CurrentTime.axis = "X"
		CurrentTime.value = str(start)
		CurrentTime.labelText = "Forecast Time"
		CurrentTime.labelPosition = "center"
		CurrentTime.labelAlignment = "center"
		CurrentTime.labelColor = "darkgray"
		CurrentTime.labelFont = "Dialog,BOLD,14"
		CurrentTime.lineColor = "gray"
		CurrentTime.lineStyle = "dash dot"
		CurrentTime.lineWidth = 2
        
        
		TopViewport_ALBO = ALBO_Plot.readViewport(0)        
		TopViewport_SALO = SALO_Plot.readViewport(0)        
		TopViewport_HARO = HARO_Plot.readViewport(0)        
		TopViewport_EUGO = EUGO_Plot.readViewport(0)        
        
		TopViewport_LOP.addAxisMarker(CurrentTime)                    
		BottomViewport_LOP.addAxisMarker(CurrentTime) 		
		TopViewport_HCR.addAxisMarker(CurrentTime)                    
		BottomViewport_HCR.addAxisMarker(CurrentTime) 		
		TopViewport_CGR.addAxisMarker(CurrentTime)                    
		BottomViewport_CGR.addAxisMarker(CurrentTime) 
		TopViewport_BLR.addAxisMarker(CurrentTime)                    
		BottomViewport_BLR.addAxisMarker(CurrentTime) 
		TopViewport_DOR.addAxisMarker(CurrentTime)                    
		BottomViewport_DOR.addAxisMarker(CurrentTime) 
		TopViewport_COT.addAxisMarker(CurrentTime)                    
		BottomViewport_COT.addAxisMarker(CurrentTime)
		TopViewport_ALBO.addAxisMarker(CurrentTime)         
		TopViewport_SALO.addAxisMarker(CurrentTime)           
		TopViewport_SALO.addAxisMarker(CurrentTime)   
		TopViewport_SALO.addAxisMarker(CurrentTime)   

        
###### Save Plot as A jpeg####


		LOP_Plot.setSize(1400, 1300)
		LOP_Plot.setLocation(100, 100)
		LOP_Plot.saveToJpeg("W:\LOP_FcstPlot.jpg")
		#LOP_Plot.close()
		
		
		HCR_Plot.setSize(1400, 1300)
		HCR_Plot.setLocation(100, 100)
		HCR_Plot.saveToJpeg("W:\HCR_FcstPlot.jpg")
		HCR_Plot.close()
		

		FAL_Plot.setSize(1400, 1300)
		FAL_Plot.setLocation(100, 100)
		FAL_Plot.saveToJpeg("W:\FAL_FcstPlot.jpg")
		FAL_Plot.close()
		
		DOR_Plot.setSize(1400, 1300)
		DOR_Plot.setLocation(100, 100)
		DOR_Plot.saveToJpeg("W:\DOR_FcstPlot.jpg")
		DOR_Plot.close()

		COT_Plot.setSize(1400, 1300)
		COT_Plot.setLocation(100, 100)
		COT_Plot.saveToJpeg("W:\COT_FcstPlot.jpg")
		COT_Plot.close()
				
		BLR_Plot.setSize(1400, 1300)
		BLR_Plot.setLocation(100, 100)
		BLR_Plot.saveToJpeg("W:\BLR_FcstPlot.jpg")
		BLR_Plot.close()
			
		CGR_Plot.setSize(1400, 1300)
		CGR_Plot.setLocation(100, 100)
		CGR_Plot.saveToJpeg("W:\CGR_FcstPlot.jpg")
		CGR_Plot.close()
		
		SALO_Plot.setSize(1400, 1300)
		SALO_Plot.setLocation(100, 100)
		SALO_Plot.saveToJpeg("W:\SALO_FcstPlot.jpg")
		SALO_Plot.close()	

		ALBO_Plot.setSize(1400, 1300)
		ALBO_Plot.setLocation(100, 100)
		ALBO_Plot.saveToJpeg("W:\ALBO_FcstPlot.jpg")
		ALBO_Plot.close()
        
		EUGO_Plot.setSize(1400, 1300)
		EUGO_Plot.setLocation(100, 100)
		EUGO_Plot.saveToJpeg("W:\EUGO_FcstPlot.jpg")
		EUGO_Plot.close()	     
        
		HARO_Plot.setSize(1400, 1300)
		HARO_Plot.setLocation(100, 100)
		HARO_Plot.saveToJpeg("W:\HARO_FcstPlot.jpg")
		HARO_Plot.close()
