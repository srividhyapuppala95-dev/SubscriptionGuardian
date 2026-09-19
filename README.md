# 🤖 Subscription & Recurring-Spend Guardian

An AI-powered prototype that helps users monitor recurring subscriptions, identify potentially unnecessary spending, detect overlapping subscriptions, and make safer subscription decisions.

## 🎯 Problem

People often subscribe to multiple digital services and forget about recurring payments. This can lead to:

- Unused subscriptions
- Unnecessary recurring expenses
- Duplicate services
- Lack of awareness about subscription usage
- Unsafe or accidental cancellation decisions

## 💡 Solution

Subscription Guardian acts as an autonomous recurring-spend assistant.

It analyzes subscription information such as:

- Subscription amount
- Last usage
- Category
- Whether the subscription is shared
- Whether the subscription belongs to a protected category

The system then recommends an appropriate action while applying safety rules before any simulated financial action.

## ⚙️ Key Features

### 🔍 Subscription Monitoring
Monitors recurring subscriptions and their usage information.

### 🧠 AI Decision Engine
Uses an AI decision engine to analyze subscription data and recommend one of the following:

- AUTO-CANCEL
- ASK USER
- KEEP
- ESCALATE

### 🔄 Overlap Detection
Detects multiple subscriptions belonging to the same category and identifies potential duplication.

### 🛡️ Safety Layer
The safety layer can override an unsafe AI decision.

Protected subscriptions, such as insurance, cannot be automatically cancelled.

### 👤 Human Approval
When a decision requires user confirmation, the system asks the user before proceeding.

### ↩️ Reversible Actions
Financial actions in this prototype are simulated and designed to be reversible.

### 🧠 Agent Memory
The prototype maintains a session-based memory of previous decisions and user choices.

### 📋 Audit Log
User-approved actions are recorded with their status, timestamp, and reversibility information.

## 🏗️ System Workflow

```text
Subscription Data
       ↓
Usage Analysis
       ↓
Overlap Detection
       ↓
AI Decision Engine
       ↓
Safety Policy
       ↓
┌───────────────────────────────┐
│                               │
↓                               ↓
AUTO-CANCEL                  ASK USER
│                               │
↓                               ↓
Simulated Action            User Decision
│                               │
└───────────────┬───────────────┘
                ↓
             Audit Log
