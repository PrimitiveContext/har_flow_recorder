# Phase 1: User ID Enumeration Hypotheses

## Backend Validation Order Theory

Most web servers validate parameters in a predictable sequence:
1. **Parameter Presence Check** - Are required fields present?
2. **Format Validation** - Do values match expected patterns?
3. **Business Logic** - Database lookups, authentication checks
4. **Security Checks** - CAPTCHA, rate limiting

## Specific Test Hypotheses

### 1. UserID Only Test
**Parameters:** `UserID=valid` (no PIN, no CAPTCHA)  
**Hypothesis:** If user validation happens before parameter validation, valid users might return "missing PIN" while invalid users return "invalid credentials"  
**Why:** Reveals if backend checks user existence before checking for required parameters

### 2. Format Validation Order
**Parameters:** `UserID=valid&PIN=123` (3 digits instead of 4)  
**Hypothesis:** Valid users might return "PIN must be 4 digits" while invalid users return generic error  
**Why:** Shows if user lookup happens before format validation

### 3. Empty vs Missing Parameters
**Test A:** `UserID=valid&PIN=&CAPTCHA=`  
**Test B:** `UserID=valid` (no PIN/CAPTCHA parameters)  
**Hypothesis:** Empty strings might bypass null checks but fail at different validation layer  
**Why:** Different code paths for null vs empty string validation

### 4. Parameter Pollution - UserID
**Parameters:** `UserID=valid&UserID=invalid`  
**Hypothesis:** Framework might take first, last, or concatenate values  
**Why:** ASP.NET typically takes last value, but configuration varies

### 5. Array Syntax Bypass
**Parameters:** `UserID[]=valid&PIN[]=1234`  
**Hypothesis:** Might bypass validation expecting string types  
**Why:** Type confusion can skip validation layers

### 6. Parameter Order Dependency
**Test A:** `UserID=valid&PIN=wrong&CAPTCHA=wrong`  
**Test B:** `CAPTCHA=wrong&PIN=wrong&UserID=valid`  
**Hypothesis:** ASP.NET often validates in model definition order  
**Why:** Could reveal which parameter triggers database lookup

### 7. Null vs Wrong Format
**Parameters:** `UserID=valid&PIN=null&CAPTCHA=null`  
**Hypothesis:** Literal "null" string might trigger different validation than empty  
**Why:** Common bug in JSON to form data conversion

### 8. Timing Attack Baseline
**Test A:** `UserID=12345678&PIN=0000&CAPTCHA=wrong`  
**Test B:** `UserID=87654321&PIN=0000&CAPTCHA=wrong`  
**Hypothesis:** Valid UserID triggers database lookup (5-20ms slower)  
**Why:** Database query adds measurable latency even with randomization

## Expected Backend Flow (ASP.NET)

```
1. Request arrives at IIS
2. ASP.NET model binding
3. [Possible timing difference] Database lookup for UserID
4. PIN hash comparison (only if user exists?)
5. CAPTCHA validation
6. Return appropriate error
```

## Key Observations
- If CAPTCHA is checked first, all invalid CAPTCHAs should have uniform timing
- If UserID is checked first, valid users will show timing delays
- Empty parameters might reveal validation order
- Parameter pollution could bypass certain checks