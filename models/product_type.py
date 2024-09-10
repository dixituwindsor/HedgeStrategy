# class ProductType:
#     MIS = "MIS"
#     NRML = "NRML"
#     CNC = "CNC"
#     MARGIN = "MARGIN"
#     BO = "BO"

class ProductType:
    DELIVERY = "DELIVERY"  # Cash & Carry for equity (CNC)
    CARRYFORWARD = "CARRYFORWARD"  # Normal for futures and options (NRML)
    MARGIN = "MARGIN"  # Margin Delivery
    INTRADAY = "INTRADAY"  # Margin Intraday Squareoff (MIS)
    BO = "BO"  # Bracket Order (Only for ROBO)
