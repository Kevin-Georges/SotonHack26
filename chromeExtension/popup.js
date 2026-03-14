document.getElementById('unlockBtn').addEventListener('click', async () => {
  const key = document.getElementById('apiKeyInput').value.trim();
  const statusDiv = document.getElementById('status');

  statusDiv.style.color = "black";
  statusDiv.innerText = "Checking your sobriety...";

  try {
    // Talk to the local Python server
    const response = await fetch('http://78.141.225.168:2600/validate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ key: key })
    });

    const data = await response.json();

    if (data.valid) {
      // Success! Set expiration for 15 minutes
      const unlockUntil = new Date().getTime() + (15 * 60 * 1000); 
      
      chrome.storage.local.set({ cartUnlockedUntil: unlockUntil }, () => {
        statusDiv.style.color = "green";
        statusDiv.innerText = "Success! Unlocking cart...";
        
        // --- NEW CODE: Automatically reload the active tab ---
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
          if (tabs.length > 0) {
            chrome.tabs.reload(tabs[0].id);
            // Optional: Close the popup automatically since we're done
            window.close(); 
          }
        });
        // ----------------------------------------------------
      });
    } else {
      // Server rejected the key
      statusDiv.style.color = "red";
      statusDiv.innerText = "Invalid Key. Put the credit card down!";
    }
  } catch (error) {
    statusDiv.style.color = "red";
    statusDiv.innerText = "Error: Make sure your Python server is running!";
    console.error("Fetch error:", error);
  }
});

// The lock button stays exactly the same
document.getElementById('lockBtn').addEventListener('click', () => {
  const statusDiv = document.getElementById('status');
  chrome.storage.local.remove('cartUnlockedUntil', () => {
    statusDiv.style.color = "#ff4757"; 
    statusDiv.innerText = "Cart LOCKED. Refreshing page...";
    
    // Let's make the lock button auto-refresh the page too!
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      if (tabs.length > 0) {
        chrome.tabs.reload(tabs[0].id);
        window.close();
      }
    });
  });
});