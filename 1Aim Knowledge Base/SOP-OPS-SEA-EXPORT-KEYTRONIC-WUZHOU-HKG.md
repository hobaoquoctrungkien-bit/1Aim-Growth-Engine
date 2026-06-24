## Metadata

| Field     | Value                              |
| --------- | ---------------------------------- |
| SOP ID    | SOP-SEA-EXP-001                    |
| Customer  | Keytronic Vietnam                  |
| Consignee | Wuzhou International Logistic (HK) |
| Service   | Sea Export LCL                     |
| Owner     | Operations                         |
| Status    | Active                             |

---

# Objective

Đảm bảo quy trình xuất khẩu hàng từ Keytronic Vietnam sang Wuzhou HKG được thực hiện đúng yêu cầu khách hàng, đúng timeline và đầy đủ chứng từ.

---

# Trigger

- Nhận Booking Confirmation
    
- Hoặc nhận yêu cầu Pick Up từ Keytronic
    

---

# Inputs

- Booking Confirmation
    
- Packing List
    
- Invoice
    
- Barcode Declaration Document
    
- SI Information
    

---

# Important Customer Notes

## Email Delivery

Hệ thống email của Keytronic đôi khi đánh dấu spam nhưng vẫn nhận được email từ 1Aim.

---

# Workflow

## STEP 1 - Send Booking Confirmation

Sau khi nhận booking:

### Send local costs

|Pallets|Local Cost|
|---|---|
|1|1,169,000 VND|
|2|1,369,000 VND|
|3|1,569,000 VND|
|4|2,169,000 VND|
|5|2,369,000 VND|
|6|2,569,000 VND|

### Confirm

- B/L Number
    

Output:

- Booking Confirmation Email Sent
    

---

## STEP 2 - Receive Pick-Up Instruction

Thông thường Keytronic sẽ gửi:

- Pick-up date
    
- Closed truck requirement
    
- Bring seal
    
- Prepare POD
    
- Driver information request
    

Output:

- Pickup Request Confirmed
    

---

## STEP 3 - One Day Before Pick-Up

Gửi email xác nhận:

Required Information:

- Truck Plate
    
- Driver Information
    
- Estimated Pick Up Time
    

Yêu cầu Keytronic cung cấp:

- Barcode Declaration Document
    
- Final Packing List
    
- Invoice Number
    

Purpose:

- Warehouse Registration
    
- POD Preparation
    

Output:

- Pickup Ready
    

---

## STEP 4 - Coordinate Charter Link

Nếu chưa có PKL:

- Request PKL from Keytronic
    
- Forward to Charter Link
    

Trước ngày lấy hàng:

- Request truck plate
    
- Driver information
    
- Pickup schedule
    

Output:

- Charter Link Ready
    

---

## STEP 5 - Prepare Pickup Documents

Chuẩn bị:

### Goods Collection Record

Required fields:

- Bill Number
    
- Invoice Number
    
- Truck Information
    
- Seal Number
    

Send to Charter Link.

Important:

- Ask driver to print document
    
- Call driver to confirm
    
- Explain Danalog warehouse entry process
    

Output:

- Pickup Documents Ready
    

---

## STEP 6 - Cargo Pickup

Verify:

- Closed Truck
    
- Seal Prepared
    
- POD Prepared
    

Collect:

- Driver Name
    
- Truck Plate
    
- Pickup Time
    

Output:

- Cargo Picked Up
    

---

## STEP 7 - Send SI Same Day

Timeline:

- Must send SI on pickup day
    

Required SI:

### Shipper

1AIM LOGISTICS CO., LTD.

### Consignee

WU ZHOU INTERNATIONAL LOGISTIC (HK) CO., LTD

### Notify Party

Same as Consignee

### Cargo Description

As provided by customer.

### BL Remark

- Exporter: KEYTRONIC VIETNAM
    
- Consignee: WU ZHOU LOGISTIC (HK) CO., LTD
    
- Total Pallets
    
- Assembled in Vietnam
    

Output:

- SI Submitted
    

---

## STEP 8 - Send Warehouse Photos

Send:

- Cargo Photos
    
- Warehouse Receipt
    

Customer must verify:

- Customs Declaration
    
- Warehouse Code
    
- POL Code
    
- Cargo Information
    

Important Notice:

Customer must report discrepancy before CFS Cut-Off.

Output:

- Warehouse Confirmation
    

---

## STEP 9 - Send Draft BL

Timeline:

- One day after pickup
    
- After warehouse measurement available
    

Request customer:

- Review Draft BL
    
- Confirm amendment before deadline
    

Customer must choose:

- Original BL
    
- Sea Waybill
    
- Telex Release
    

If no response:

- Treat as BL approved
    

Output:

- BL Approved
    

---

## STEP 10 - Completion

Send appreciation email.

Output:

- Shipment Closed
    

---

# Checklist

## Booking

-  Booking received
    
-  BL number confirmed
    
-  Local charges sent
    

## Pickup

-  PKL received
    
-  Invoice received
    
-  Barcode Declaration received
    
-  Truck assigned
    
-  Driver assigned
    
-  POD prepared
    
-  Seal prepared
    

## Operations

-  Pickup completed
    
-  SI sent
    
-  Warehouse photos sent
    
-  Draft BL sent
    
-  BL approved
    

## Closing

-  Final documents issued
    
-  Customer thanked
    

---

# Lessons Learned

- Always request Barcode Declaration one day before pickup.
    
- Always obtain Invoice Number before preparing POD.
    
- Call driver before pickup and explain Danalog entry procedure.
    
- SI must be submitted on pickup day.
    
- Customer must confirm BL type before release.