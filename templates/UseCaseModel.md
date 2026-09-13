# Use-Case Model Template: Full-Stack Software Program

This document serves as a template and guide for creating a comprehensive Use-Case Model for a full-stack software application. It bridges the gap between user requirements and technical implementation, covering both frontend (user interactions) and backend (system responses, database updates).

---

## 1. Introduction
### 1.1 Purpose
Define the purpose of this use-case model. (e.g., "To capture the functional requirements of the [System Name] and describe how users will interact with the system.")

### 1.2 Scope
Briefly describe what is in scope and out of scope for this system.

### 1.3 Definitions, Acronyms, and Abbreviations
List any domain-specific terms used in the document to ensure all stakeholders share a common understanding.

---

## 2. System Boundary & Actors
Define who and what interacts with the system. In a full-stack context, actors can be human users or external systems/APIs.

### 2.1 Primary Actors
Users whose goals are fulfilled by the system.
* **[Actor 1]** (e.g., *Customer*): Briefly describe their role and goals.
* **[Actor 2]** (e.g., *Admin*): Briefly describe their role and privileges.

### 2.2 Secondary / System Actors
External entities that provide a service to the system.
* **[External System 1]** (e.g., *Payment Gateway - Stripe*): Handles transaction processing.
* **[External System 2]** (e.g., *Email Service - SendGrid*): Sends automated notifications.

---

## 3. Use-Case Diagram
*Insert a Use-Case Diagram here (e.g., exported from UML tools like Lucidchart, Draw.io, or PlantUML).*

**Diagram Description:** A brief narrative explaining the visual diagram, highlighting the main interactions between the actors and the system boundaries.

---

## 4. Use-Case Specifications
*This is the core of the document. Every major feature should have a detailed use case. Below is a standard template to duplicate for each use case.*

### UC-01: [Action Verb + Noun, e.g., "Process Customer Checkout"]

**1. Brief Description**
A short summary of what the use case achieves. (e.g., "Allows a customer to review their cart, enter shipping details, and pay for their order.")

**2. Actors**
* **Primary:** [e.g., Customer]
* **Secondary:** [e.g., Payment Gateway]

**3. Pre-conditions**
What must be true *before* the use case can begin?
* *Frontend:* User is logged in and has items in their cart.
* *Backend/DB:* Database connection is active; items in cart are in stock.

**4. Post-conditions**
What is the state of the system *after* the use case successfully completes?
* *System State:* Order is saved in the database with status 'Pending'.
* *Output:* Payment receipt is sent to the user's email; cart is emptied.

**5. Main Success Scenario (Happy Path)**
Step-by-step description of the standard interaction between the Actor and the System (Frontend + Backend).
1. **Actor:** Clicks "Proceed to Checkout".
2. **System (Frontend):** Requests shipping and billing information.
3. **Actor:** Enters shipping and billing information and submits.
4. **System (Backend):** Validates the data format and calculates taxes/shipping.
5. **System (Frontend):** Displays the final total to the user.
6. **Actor:** Confirms and clicks "Pay Now".
7. **System (Backend):** Sends payment details to [Payment Gateway].
8. **[Payment Gateway]:** Confirms successful transaction.
9. **System (Backend):** Creates Order record in DB, clears cart, and triggers email notification.
10. **System (Frontend):** Redirects user to "Order Success" page.

**6. Alternative Flows (Extensions)**
What happens if the user chooses a different valid path?
* **3a. User selects "Use Saved Address":**
    1. System populates the form with the default address from the database.
    2. Resume at step 4.

**7. Exceptions (Error Flows)**
What happens if things go wrong? (Crucial for full-stack error handling).
* **4a. Validation Fails (e.g., Invalid Zip Code):**
    1. System (Backend) rejects data.
    2. System (Frontend) highlights the incorrect field with an error message.
    3. Use case pauses until the user corrects the data.
* **8a. Payment Declined:**
    1. System (Backend) logs the failed attempt.
    2. System (Frontend) displays "Payment Declined" and prompts for a different payment method.

**8. Special Requirements (Non-Functional Requirements)**
* **Performance:** Payment processing must time out after 10 seconds.
* **Security:** Payment details must be tokenized and never stored in the local database.

---

### UC-02: [Next Use Case Name]
*(Repeat the structure from UC-01)*

---

## 5. Traceability Matrix (Optional but Recommended)
A table linking Use Cases to specific Business Requirements or User Stories (e.g., Jira Tickets).

| Use Case ID | Use Case Name | Requirement ID / Jira Epic |
| :--- | :--- | :--- |
| UC-01 | Process Customer Checkout | REQ-101, EPIC-23 |
| UC-02 | Register New User | REQ-055, EPIC-12 |

---

## 6. Appendix
Any additional diagrams, mockups (wireframes linking frontend views to use cases), or API architectural references that support the use cases.
