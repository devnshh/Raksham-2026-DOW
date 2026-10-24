package com.raksham.upi.ui.screens

import com.raksham.upi.ui.formatAmount
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.FastForward
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.raksham.risk.RiskGate
import com.raksham.upi.simulation.*
import com.raksham.upi.ui.theme.Motion
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun SimulationLabScreen(
    onBackClick: () -> Unit,
    onOpenCustom: (contact: com.raksham.upi.data.Contact, amount: Double, entryChannel: String, note: String,
                   signals: com.raksham.risk.session.SessionSignals) -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }

    var apiUrlText by remember { mutableStateOf(RiskGate.getBaseUrl()) }
    var selectedScenarioId by remember { mutableStateOf(ScenarioCatalog.scenarios.first().id) }

    // Execution & Step state
    var isRunning by remember { mutableStateOf(false) }
    var currentStep by remember { mutableStateOf(StepProgress.IDLE) }
    var currentTypingPreview by remember { mutableStateOf("") }
    var resultsMap by remember { mutableStateOf<Map<String, ScenarioExecutionResult>>(emptyMap()) }

    val selectedScenario = ScenarioCatalog.scenarios.firstOrNull { it.id == selectedScenarioId }
        ?: ScenarioCatalog.scenarios.first()

    fun showMessage(text: String) {
        coroutineScope.launch {
            snackbar.currentSnackbarData?.dismiss()
            snackbar.showSnackbar(text)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Simulation Lab") },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = {
            Surface(color = MaterialTheme.colorScheme.surfaceContainer) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            resultsMap = emptyMap()
                            currentStep = StepProgress.IDLE
                            currentTypingPreview = ""
                            showMessage("State reset")
                        },
                        enabled = !isRunning,
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp)
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Reset")
                    }

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
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp)
                    ) {
                        if (isRunning) {
                            CircularProgressIndicator(color = LocalContentColor.current, strokeWidth = 2.dp, modifier = Modifier.size(18.dp))
                        } else {
                            Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Run")
                        }
                    }

                    FilledTonalButton(
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
                        modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp)
                    ) {
                        Icon(Icons.Default.FastForward, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Run all", maxLines = 1)
                    }
                }
            }
        }
    ) { padding ->
        LazyColumn(
            contentPadding = padding,
            modifier = Modifier.fillMaxSize()
        ) {
            item { LabSectionHeader("Risk API") }
            item {
                OutlinedTextField(
                    value = apiUrlText,
                    onValueChange = {
                        apiUrlText = it
                        RiskGate.setBaseUrl(it)
                    },
                    label = { Text("Backend API endpoint") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)
                )
                Row(Modifier.fillMaxWidth().padding(horizontal = 8.dp), horizontalArrangement = Arrangement.End) {
                    TextButton(
                        onClick = {
                            RiskGate.setBaseUrl(apiUrlText)
                            RiskGate.warmUp()
                            showMessage("Saved API URL")
                        }
                    ) { Text("Save") }
                }
            }

            item { LabSectionHeader("Custom scenario") }
            item { CustomScenarioCard(onOpen = onOpenCustom) }

            item { LabSectionHeader("Progress") }
            item {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    StepItem("1", "Entering payee", currentStep == StepProgress.ENTERING_PAYEE, currentStep == StepProgress.CHECKING || currentStep == StepProgress.RESULT)
                    Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                    StepItem("2", "Checking", currentStep == StepProgress.CHECKING, currentStep == StepProgress.RESULT)
                    Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, contentDescription = null, tint = MaterialTheme.colorScheme.outline)
                    StepItem("3", "Result", currentStep == StepProgress.RESULT, false)
                }
                AnimatedVisibility(
                    visible = isRunning && currentTypingPreview.isNotBlank(),
                    enter = expandVertically(tween(Motion.MEDIUM, easing = Motion.EmphasizedDecelerate)) + fadeIn(tween(Motion.MEDIUM)),
                    exit = shrinkVertically(tween(Motion.SHORT, easing = Motion.EmphasizedAccelerate)) + fadeOut(tween(Motion.SHORT))
                ) {
                    Surface(
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.surfaceContainerHigh,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                    ) {
                        Text(
                            "Typing preview: $currentTypingPreview",
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                        )
                    }
                }
            }

            item { LabSectionHeader("Scenarios") }
            items(ScenarioCatalog.scenarios, key = { it.id }) { sc ->
                val isSelected = sc.id == selectedScenarioId
                val result = resultsMap[sc.id]
                val rowColor by animateColorAsState(
                    if (isSelected) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surface,
                    tween(Motion.SHORT),
                    label = "scenario row"
                )
                ListItem(
                    leadingContent = { RadioButton(selected = isSelected, onClick = null) },
                    headlineContent = { Text("${sc.titleEn} (${sc.titleHi})") },
                    supportingContent = {
                        Column {
                            Text(sc.caption)
                            Text(
                                "To: ${sc.payeeName} (${sc.payeeVpa}) · ₹${formatAmount(sc.amount)}",
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                            if (result != null) {
                                Text("Expected: ${sc.humanExpectedLabel}")
                                Text(
                                    "Actual: ${result.humanResultLabel}",
                                    color = if (result.isPassed) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.error
                                )
                            }
                        }
                    },
                    trailingContent = if (result != null) {
                        {
                            Surface(
                                shape = CircleShape,
                                color = if (result.isPassed) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.errorContainer
                            ) {
                                Text(
                                    if (result.isPassed) "Pass" else "Fail",
                                    style = MaterialTheme.typography.labelLarge,
                                    color = if (result.isPassed) MaterialTheme.colorScheme.onTertiaryContainer else MaterialTheme.colorScheme.onErrorContainer,
                                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
                                )
                            }
                        }
                    } else null,
                    colors = ListItemDefaults.colors(containerColor = rowColor),
                    modifier = Modifier
                        .animateItemPlacement()
                        .selectable(selected = isSelected, enabled = !isRunning, role = Role.RadioButton) {
                            selectedScenarioId = sc.id
                        }
                )
            }
        }
    }
}

@Composable
private fun LabSectionHeader(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(start = 16.dp, end = 16.dp, top = 24.dp, bottom = 8.dp)
    )
}

@Composable
private fun StepItem(
    number: String,
    label: String,
    isActive: Boolean,
    isDone: Boolean
) {
    val circle by animateColorAsState(
        when {
            isDone -> MaterialTheme.colorScheme.tertiary
            isActive -> MaterialTheme.colorScheme.primary
            else -> MaterialTheme.colorScheme.surfaceContainerHighest
        },
        tween(Motion.SHORT),
        label = "step circle"
    )
    val onCircle = when {
        isDone -> MaterialTheme.colorScheme.onTertiary
        isActive -> MaterialTheme.colorScheme.onPrimary
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier.size(24.dp).background(circle, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            if (isDone) {
                Icon(Icons.Default.Check, contentDescription = null, tint = onCircle, modifier = Modifier.size(14.dp))
            } else {
                Text(number, style = MaterialTheme.typography.labelMedium, color = onCircle)
            }
        }
        Spacer(Modifier.width(6.dp))
        Text(
            label,
            style = MaterialTheme.typography.labelMedium,
            color = if (isActive || isDone) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
