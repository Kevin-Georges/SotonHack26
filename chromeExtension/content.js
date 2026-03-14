console.log("Impulse Guard is active. Scanning for checkout buttons...");

// --- CONFIGURATION ---
const TEST_MODE = true; // Set to true to force lock 24/7 for testing! Change to false for final demo.
const DANGER_START = 22; // 10 PM
const DANGER_END = 4;    // 4 AM


function checkCartStatus() {
  const currentHour = new Date().getHours();
  const isDangerTime = currentHour >= DANGER_START || currentHour < DANGER_END;

  // If we aren't in test mode and it's daytime, do nothing.
  if (!TEST_MODE && !isDangerTime) {
    console.log("Safe hours. Shopping allowed.");
    return;
  }

  // Check if they have a valid unlock key in storage
  chrome.storage.local.get(['cartUnlockedUntil'], (result) => {
    const now = new Date().getTime();
    const unlockedUntil = result.cartUnlockedUntil || 0;

    if (now < unlockedUntil) {
      console.log("Valid unlock key found. Proceed to checkout.");
      // Stop checking, let them buy
    } else {
      console.log("No valid key. Initiating lockdown.");
      // Start a loop to aggressively hunt down the checkout buttons
      setInterval(lockTheCart, 1000); 
    }
  });
}

function lockTheCart() {
  const selectors = [
    '[name="proceedToRetailCheckout"]', 
    '#buy-now-button',
    'input[aria-labelledby="submit.buy-now-announce"]'
  ];

  selectors.forEach(selector => {
    const buttons = document.querySelectorAll(selector);
    
    buttons.forEach(button => {
      if (button.getAttribute('data-locked') === 'true') return;

      // 1. Disable the actual functional button
      button.disabled = true;
      button.style.cursor = "not-allowed";
      button.setAttribute('data-locked', 'true');

      // 2. Intercept the click event
      button.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        alert("Impulse Guard: Put the credit card down! Go to impulseguard.com to pass your sobriety test first.");
      }, true);

      // 3. Hack Amazon's specific visual layers
      const parentInner = button.closest('.a-button-inner');
      if (parentInner) {
        // Turn the background red and strip away Amazon's gradient
        parentInner.style.setProperty('background-color', '#ff4757', 'important');
        parentInner.style.setProperty('background-image', 'none', 'important');
        parentInner.style.setProperty('box-shadow', 'none', 'important');
        
        // Find Amazon's overlapping text span and change it
        const textSpan = parentInner.querySelector('.a-button-text');
        if (textSpan) {
          textSpan.innerText = "LOCKED: Pass Sobriety Test";
          textSpan.style.setProperty('color', '#000000', 'important'); // Black text
          textSpan.style.setProperty('font-weight', 'bold', 'important');
        }
      } else {
        // Fallback just in case Amazon changes their HTML structure tomorrow
        button.style.setProperty('background-color', '#ff4757', 'important');
        button.style.setProperty('color', '#000000', 'important');
        if (button.tagName === 'INPUT') button.value = "LOCKED: Pass Sobriety Test";
      }
      
      console.log("Button successfully locked and styled!");
    });
  });
}

let modalInjected = false;

function spawnUnlockModal() {
  // If we already injected the popup, don't do it again
  if (modalInjected) return;
  modalInjected = true;

  // Create a dark overlay that covers the whole screen
  const overlay = document.createElement('div');
  overlay.id = 'impulse-guard-overlay';
  overlay.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(0,0,0,0.85); z-index: 9999999; /* Max Z-index to sit on top of everything */
    display: flex; justify-content: center; align-items: center;
    backdrop-filter: blur(5px);
  `;

  // Create the white popup box
  const modal = document.createElement('div');
  modal.style.cssText = `
    background: white; padding: 30px; border-radius: 12px;
    text-align: center; font-family: Arial, sans-serif; width: 320px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
  `;

  // Add the HTML content inside the popup
  modal.innerHTML = `
    <h2 style="margin-top:0; color:#ff4757; font-size: 24px;">Impulse Guard</h2>
    <p style="color: #333; font-size: 16px;">It's late. Your cart is <b>LOCKED</b>.</p>
    <input type="text" id="ig-api-key" placeholder="Enter Unlock Key (e.g. IG-123)" 
           style="width: 90%; padding: 10px; margin: 15px 0; border: 2px solid #ccc; border-radius: 6px; font-size: 14px;">
    <button id="ig-unlock-btn" 
            style="background:#2ed573; color:white; border:none; padding:12px 20px; border-radius: 6px; cursor:pointer; font-weight:bold; width:100%; font-size: 16px;">
      Unlock Checkout
    </button>
    <p id="ig-error" style="color:#ff4757; font-size:14px; display:none; font-weight: bold; margin-top: 10px;">Invalid Key!</p>
    <p style="font-size:14px; margin-top:20px; color: #666;">
      Need a key? <a href="#" style="color:#3742fa; font-weight:bold; text-decoration:none;">Take the Sobriety Test</a>
    </p>
  `;

  // Attach the box to the overlay, and the overlay to the webpage
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  // Add the unlock logic to this injected button
  document.getElementById('ig-unlock-btn').addEventListener('click', () => {
    const key = document.getElementById('ig-api-key').value;
    
    if (key.startsWith('IG-')) {
      const unlockUntil = new Date().getTime() + (15 * 60 * 1000); 
      chrome.storage.local.set({ cartUnlockedUntil: unlockUntil }, () => {
        // If successful, instantly reload the page to clear the lock
        window.location.reload(); 
      });
    } else {
      document.getElementById('ig-error').style.display = 'block';
    }
  });
}
// Run the initial check
checkCartStatus();