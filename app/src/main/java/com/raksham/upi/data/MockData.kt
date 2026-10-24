package com.raksham.upi.data

data class Contact(
    val id: String,
    val name: String,
    val phone: String,
    val upiId: String,
    val avatarInitials: String,
    val colorHex: Long,
    val isVerified: Boolean = false
)

data class BankAccount(
    val id: String,
    val bankName: String,
    val accountNumberMasked: String,
    val isPrimary: Boolean = false,
    val accountType: String = "Savings Account"
)

data class TransactionItem(
    val id: String,
    val title: String,
    val subtitle: String,
    val amount: Double,
    val isCredit: Boolean,
    val dateString: String,
    val verifiedSafe: Boolean = true,
    val upiRefId: String
)

object MockData {

    val currentUserUpiId = "raksham@oksbi"
    val currentUserName = "Ujjawal (You)"

    val linkedBankAccounts = listOf(
        BankAccount("b1", "State Bank of India", "•••• 4291", isPrimary = true),
        BankAccount("b2", "HDFC Bank", "•••• 8820", isPrimary = false),
        BankAccount("b3", "ICICI Bank", "•••• 1944", isPrimary = false)
    )

    val contacts = listOf(
        Contact("c1", "Rahul Sharma", "+91 98765 43210", "rahul.sharma@oksbi", "RS", 0xFF1A73E8),
        Contact("c2", "Priya Verma", "+91 98111 22334", "priya.verma@okaxis", "PV", 0xFF0D652D),
        Contact("c3", "Amit Patel", "+91 98222 55667", "amit.patel@ibl", "AP", 0xFFB06000),
        Contact("c4", "Sneha Rao", "+91 98444 88990", "sneha.rao@paytm", "SR", 0xFF7627BB),
        Contact("c5", "Vikram Singh", "+91 98777 11223", "vikram.singh@okhdfcbank", "VS", 0xFFD93025),
        Contact("c6", "Anjali Mehta", "+91 98999 44332", "anjali.mehta@oksbi", "AM", 0xFF007B83),
        Contact("c7", "Chai Point", "Merchant Counter", "chaipoint@icici", "CP", 0xFF137333, isVerified = true),
        Contact("c8", "Zomato", "Online Orders", "zomato@hdfcbank", "ZO", 0xFFD93025, isVerified = true)
    )

    val sampleScamPayees = listOf(
        Contact("scam1", "CBI Cyber Cell Support", "+91 99999 00001", "cbi-verification-dept@ybl", "CB", 0xFFD93025),
        Contact("scam2", "SBI Quick KYC Helpdesk", "+91 99999 00002", "kyc-helpdesk-update@ybl", "KY", 0xFFD93025),
        Contact("scam3", "Amazon Refund Resolution", "+91 99999 00003", "amaz0n-refund-desk@okaxis", "AM", 0xFFD93025)
    )

    val recentTransactions = listOf(
        TransactionItem("t1", "Chai Point", "Paid via QR", 45.0, isCredit = false, "Today, 5:15 PM", verifiedSafe = true, "429108394821"),
        TransactionItem("t2", "Priya Verma", "Split dinner bill", 350.0, isCredit = true, "Yesterday, 9:30 PM", verifiedSafe = true, "429107129482"),
        TransactionItem("t3", "Zomato", "Food Delivery", 420.0, isCredit = false, "18 Oct 2026", verifiedSafe = true, "429094827103"),
        TransactionItem("t4", "Rahul Sharma", "Monthly gym split", 800.0, isCredit = false, "15 Oct 2026", verifiedSafe = true, "428987462194"),
        TransactionItem("t5", "BESCOM Electricity", "Bill Payment", 1250.0, isCredit = false, "10 Oct 2026", verifiedSafe = true, "428876541290")
    )
}

