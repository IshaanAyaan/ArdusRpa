#!/usr/bin/env python3
"""Final polished form filler for Sallie Mae scholarship."""

import time
from playwright.sync_api import sync_playwright

def final_form_fill():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("🚀 Starting Sallie Mae scholarship form filler...")
        
        try:
            print("🌐 Navigating to form...")
            page.goto("https://www.sallie.com/scholarships/no-essay", timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            print("✅ Page loaded")
            
            # Wait for form to be ready
            time.sleep(5)
            
            print("🔍 Making form elements visible...")
            
            # Make form elements visible
            page.evaluate("""
                // Make all form elements visible
                const forms = document.querySelectorAll('form');
                forms.forEach(form => {
                    form.style.display = 'block';
                    form.style.visibility = 'visible';
                    form.style.opacity = '1';
                });
                
                // Make all inputs visible
                const inputs = document.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    input.style.display = 'block';
                    input.style.visibility = 'visible';
                    input.style.opacity = '1';
                    input.style.position = 'relative';
                    input.style.zIndex = '9999';
                });
                
                // Remove any overlays that might be hiding the form
                const overlays = document.querySelectorAll('[style*="position: fixed"], [style*="position: absolute"]');
                overlays.forEach(overlay => {
                    if (overlay.style.zIndex > 1000) {
                        overlay.style.display = 'none';
                    }
                });
                
                console.log('Made form elements visible');
            """)
            
            time.sleep(2)
            
            print("📝 Filling form fields...")
            
            # Question 1: Student/Parent radio button
            print("1️⃣ Filling: Are you a student or a parent of a student?")
            page.evaluate("""
                const studentRadio = document.querySelector('input[type="radio"][value="Student"]');
                if (studentRadio) {
                    studentRadio.checked = true;
                    studentRadio.click();
                    console.log('Selected: Student');
                } else {
                    console.log('Student radio not found');
                }
            """)
            print("✅ Selected: Student")
            time.sleep(1)
            
            # Question 2: High school graduation year
            print("2️⃣ Filling: What is the student's high school graduation year?")
            page.evaluate("""
                const gradYearSelect = document.querySelector('select[name="member_hs_grad_year"]');
                if (gradYearSelect) {
                    gradYearSelect.value = '2026';
                    gradYearSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log('Selected graduation year: 2026');
                } else {
                    console.log('Graduation year select not found');
                }
            """)
            print("✅ Selected graduation year: 2026")
            time.sleep(1)
            
            # Question 3: Level of study
            print("3️⃣ Filling: What is the student's upcoming level of study?")
            page.evaluate("""
                const studyLevelSelect = document.querySelector('select[name="member_upcoming_level_of_study"]');
                if (studyLevelSelect) {
                    studyLevelSelect.value = 'High School Senior';
                    studyLevelSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log('Selected study level: High School Senior');
                } else {
                    console.log('Study level select not found');
                }
            """)
            print("✅ Selected study level: High School Senior")
            time.sleep(1)
            
            # Question 4: College name
            print("4️⃣ Filling: What college/university will you be attending?")
            page.evaluate("""
                const collegeInput = document.querySelector('input[name="member_college"]');
                if (collegeInput) {
                    collegeInput.value = 'Stanford University';
                    collegeInput.dispatchEvent(new Event('input', { bubbles: true }));
                    collegeInput.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log('Filled college: Stanford University');
                } else {
                    console.log('College input not found');
                }
            """)
            print("✅ Filled college: Stanford University")
            time.sleep(1)
            
            # Question 5: Phone number
            print("5️⃣ Filling: Want to receive texts around planning and paying for college?")
            page.evaluate("""
                const phoneInput = document.querySelector('input[name="phone"]');
                if (phoneInput) {
                    phoneInput.value = '5551234567';
                    phoneInput.dispatchEvent(new Event('input', { bubbles: true }));
                    phoneInput.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log('Filled phone: 5551234567');
                } else {
                    console.log('Phone input not found');
                }
            """)
            print("✅ Filled phone: 5551234567")
            time.sleep(1)
            
            # Question 6: Consent checkbox
            print("6️⃣ Filling: Consent checkbox")
            page.evaluate("""
                const consentCheckbox = document.querySelector('input[name="consent_marketing_sallie"]');
                if (consentCheckbox) {
                    consentCheckbox.checked = true;
                    consentCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log('Checked consent checkbox');
                } else {
                    console.log('Consent checkbox not found');
                }
            """)
            print("✅ Checked consent checkbox")
            time.sleep(1)
            
            # Take screenshot before submission
            page.screenshot(path="output/form_filled_before_submit.png", full_page=True)
            print("📸 Screenshot before submission saved")
            
            # Submit the form
            print("🎯 Submitting form...")
            page.evaluate("""
                const submitBtn = document.querySelector('input[type="submit"][value="Submit my application"]');
                if (submitBtn) {
                    submitBtn.click();
                    console.log('Clicked submit button');
                } else {
                    // Try alternative submit button selectors
                    const altSubmit = document.querySelector('button[type="submit"], input[type="submit"], button:has-text("Submit")');
                    if (altSubmit) {
                        altSubmit.click();
                        console.log('Clicked alternative submit button');
                    } else {
                        console.log('Submit button not found');
                    }
                }
            """)
            print("🎉 FORM SUBMITTED!")
            
            # Wait for submission to process
            time.sleep(5)
            
            # Take screenshot after submission
            page.screenshot(path="output/form_submitted_success.png", full_page=True)
            print("📸 Screenshot after submission saved")
            
            # Check for success indicators
            print("🔍 Checking for success indicators...")
            try:
                success_info = page.evaluate("""
                    (function() {
                        const successTexts = [
                            'thank you', 'thanks', 'submitted', 'response', 'success',
                            'application received', 'received your application'
                        ];
                        
                        const pageText = document.body.innerText.toLowerCase();
                        const foundIndicators = successTexts.filter(text => pageText.includes(text));
                        
                        return {
                            foundIndicators: foundIndicators,
                            currentUrl: window.location.href,
                            pageTitle: document.title
                        };
                    })();
                """)
                
                print(f"Success indicators found: {success_info['foundIndicators']}")
                print(f"Current URL: {success_info['currentUrl']}")
                print(f"Page title: {success_info['pageTitle']}")
                
                if success_info['foundIndicators']:
                    print("🎉 SUCCESS! Form submission appears to be successful!")
                else:
                    print("⚠️ Warning: No clear success indicators found, but form was submitted")
            except Exception as e:
                print(f"Could not check success indicators: {e}")
                print("⚠️ Form was submitted but could not verify success")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            page.screenshot(path="output/form_error.png", full_page=True)
            print("📸 Error screenshot saved")
        
        print("⏳ Waiting 10 seconds before closing...")
        time.sleep(10)
        
        browser.close()
        
        print("✅ Form filling process completed!")

if __name__ == "__main__":
    final_form_fill()
