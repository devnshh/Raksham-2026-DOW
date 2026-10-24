package com.raksham.upi.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.raksham.risk.RiskGate
import com.raksham.upi.simulation.*
import com.raksham.upi.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SimulationLabScreen(
    onBackClick: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var apiUrlText by remember { mutableStateOf(RiskGate.getBaseUrl()) }
    var selectedScenarioId by remember { mutableStateOf(ScenarioCatalog.scenarios.first().id) }

    // Execution & Step state
    var isRunning by remember { mutableStateOf(false) }
    var currentStep by remember { mutableStateOf(StepProgress.IDLE) }
    var currentTypingPreview by remember { mutableStateOf("") }
    var resultsMap by remember { mutableStateOf<Map<String, ScenarioExecutionResult>>(emptyMap()) }

    val selectedScenario = ScenarioCatalog.scenarios.firstOrNull { it.id == selectedScenarioId }
        ?: ScenarioCatalog.scenarios.first()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "Simulation Lab",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = Color(0xFF2563EB)
                        ) {
                            Text(
                                text = "AUTOMATED SUITE",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF0F172A))
            )
        },
        containerColor = SurfaceBackground
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            // 1. Step Strip (Entering payee -> Checking -> Result)
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = Color(0xFF1E293B),
                tonalElevation = 2.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    StepItem(
                        number = "1",
                        label = "Entering Payee",
                        isActive = currentStep == StepProgress.ENTERING_PAYEE,
                        isDone = currentStep == StepProgress.CHECKING || currentStep == StepProgress.RESULT
                    )
                    Text("→", color = Color(0xFF64748B), fontWeight = FontWeight.Bold)
                    StepItem(
                        number = "2",
                        label = "Checking",
                        isActive = currentStep == StepProgress.CHECKING,
                        isDone = currentStep == StepProgress.RESULT
                    )
                    Text("→", color = Color(0xFF64748B), fontWeight = FontWeight.Bold)
                    StepItem(
                        number = "3",
                        label = "Result",
                        isActive = currentStep == StepProgress.RESULT,
                        isDone = false
                    )
                }
            }

            // 2. Target Server Configuration Card
            Surface(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(14.dp),
                shape = RoundedCornerShape(14.dp),
                color = Color.White,
                tonalElevation = 1.dp
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        text = "Backend API Endpoint (Port 8000)",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextSecondary
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedTextField(
                            value = apiUrlText,
                            onValueChange = {
                                apiUrlText = it
                                RiskGate.setBaseUrl(it)
                            },
                            singleLine = true,
                            textStyle = LocalTextStyle.current.copy(fontSize = 13.sp),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.weight(1f)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Button(
                            onClick = {
                                RiskGate.setBaseUrl(apiUrlText)
                                Toast.makeText(context, "Saved API URL", Toast.LENGTH_SHORT).show()
                            },
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = GPayBlue),
                            modifier = Modifier.height(50.dp)
                        ) {
                            Text("Save", fontSize = 13.sp)
                        }
                    }
                }
            }

            // Typing Animation Status (if active)
            if (isRunning && currentTypingPreview.isNotBlank()) {
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = Color(0xFFF1F5F9),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 14.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = "Typing preview: $currentTypingPreview",
                        fontSize = 12.sp,
                        color = TextSecondary,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                    )
                }
            }

            // 3. Scenario List
            LazyColumn(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(ScenarioCatalog.scenarios) { sc ->
                    val isSelected = sc.id == selectedScenarioId
                    val result = resultsMap[sc.id]

                    Surface(
                        shape = RoundedCornerShape(14.dp),
                        color = if (isSelected) Color(0xFFEFF6FF) else Color.White,
                        border = if (isSelected) ButtonDefaults.outlinedButtonBorder else null,
                        tonalElevation = 1.dp,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(14.dp))
                            .clickable {
                                if (!isRunning) selectedScenarioId = sc.id
                            }
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = "${sc.titleEn} (${sc.titleHi})",
                                        fontSize = 15.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = TextPrimary
                                    )
                                    Text(
                                        text = sc.caption,
                                        fontSize = 12.sp,
                                        color = TextSecondary,
                                        modifier = Modifier.padding(top = 2.dp)
                                    )
                                    Text(
                                        text = "To: ${sc.payeeName} (${sc.payeeVpa}) • ₹${String.format("%,.0f", sc.amount)}",
                                        fontSize = 12.sp,
                                        color = TextMuted,
                                        modifier = Modifier.padding(top = 2.dp)
                                    )
                                }

                                if (result != null) {
                                    Surface(
                                        shape = RoundedCornerShape(6.dp),
                                        color = if (result.isPassed) Color(0xFFDCFCE7) else Color(0xFFFEE2E2),
                                        modifier = Modifier.padding(start = 8.dp)
                                    ) {
                                        Text(
                                            text = if (result.isPassed) "PASS" else "FAIL",
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = if (result.isPassed) Color(0xFF15803D) else Color(0xFFB91C1C),
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                        )
                                    }
                                }
                            }

                            if (result != null) {
                                Spacer(modifier = Modifier.height(8.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        text = "Expected: ${sc.humanExpectedLabel}",
                                        fontSize = 11.sp,
                                        color = TextSecondary
                                    )
                                    Text(
                                        text = "Actual: ${result.humanResultLabel}",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = if (result.isPassed) Color(0xFF15803D) else Color(0xFFB91C1C)
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // 4. Lab Action Buttons (Run, Run All, Reset)
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = Color.White,
                tonalElevation = 4.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // Reset Button
                    OutlinedButton(
                        onClick = {
                            resultsMap = emptyMap()
                            currentStep = StepProgress.IDLE
                            currentTypingPreview = ""
                            Toast.makeText(context, "State reset", Toast.LENGTH_SHORT).show()
                        },
                        enabled = !isRunning,
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp)
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Reset", fontSize = 13.sp)
                    }

                    // Run Selected Scenario
                    Button(
                        onClick = {
                            isRunning = true
                            coroutineScope.launch {
                                val res = ScenarioPlayer.playScenario(
                                    scenario = selectedScenario,
                                    onStepChanged = { currentStep = it },
                                    onTypingProgress = { amt, note ->
                                        currentTypingPreview = "₹$amt ($note)"
                                    }
                                )
                                resultsMap = resultsMap + (selectedScenario.id to res)
                                isRunning = false
                                currentStep = StepProgress.RESULT
                            }
                        },
                        enabled = !isRunning,
                        colors = ButtonDefaults.buttonColors(containerColor = GPayBlue),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .weight(1.2f)
                            .height(48.dp)
                    ) {
                        if (isRunning) {
                            CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(18.dp))
                        } else {
                            Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Run", fontSize = 14.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    // Run All Scenarios
                    Button(
                        onClick = {
                            isRunning = true
                            coroutineScope.launch {
                                for (sc in ScenarioCatalog.scenarios) {
                                    selectedScenarioId = sc.id
                                    val res = ScenarioPlayer.playScenario(
                                        scenario = sc,
                                        onStepChanged = { currentStep = it },
                                        onTypingProgress = { amt, note ->
                                            currentTypingPreview = "₹$amt ($note)"
                                        }
                                    )
                                    resultsMap = resultsMap + (sc.id to res)
                                    delay(500L) // short pause between scenarios
                                }
                                isRunning = false
                                currentStep = StepProgress.RESULT
                            }
                        },
                        enabled = !isRunning,
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0F172A)),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .weight(1.3f)
                            .height(48.dp)
                    ) {
                        Icon(Icons.Default.FastForward, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Run All", fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

@Composable
private fun StepItem(
    number: String,
    label: String,
    isActive: Boolean,
    isDone: Boolean
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(24.dp)
                .background(
                    color = if (isDone) Color(0xFF10B981) else if (isActive) Color(0xFF38BDF8) else Color(0xFF475569),
                    shape = CircleShape
                ),
            contentAlignment = Alignment.Center
        ) {
            if (isDone) {
                Icon(Icons.Default.Check, contentDescription = null, tint = Color.White, modifier = Modifier.size(14.dp))
            } else {
                Text(text = number, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
            }
        }
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = label,
            fontSize = 12.sp,
            fontWeight = if (isActive || isDone) FontWeight.Bold else FontWeight.Normal,
            color = if (isActive || isDone) Color.White else Color(0xFF94A3B8)
        )
    }
}
