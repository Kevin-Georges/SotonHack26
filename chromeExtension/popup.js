document.getElementById('unlockBtn').addEventListener('click', () => {
  const key = document.getElementById('apiKeyInput').value;
  const statusDiv = document.getElementById('status');

  // MVP Hack: For now, we just check if the key starts with "IG-" 
  // Later, you can make this verify against your actual Python backend!
  if (key.startsWith('IG-')) {
    
    // Set an expiration time (e.g., 15 minutes from now)
    const unlockUntil = new Date().getTime() + (15 * 60 * 1000); 
    
    // Save the unlock status to Chrome storage
    chrome.storage.local.set({ cartUnlockedUntil: unlockUntil }, () => {
      statusDiv.style.color = "green";
      statusDiv.innerText = "Success! Cart unlocked for 15 minutes. Refresh your page.";
    });
    
  } else {
    statusDiv.style.color = "red";
    statusDiv.innerText = "Invalid Key. Go pass the sobriety test!";
  }
});

document.getElementById('lockBtn').addEventListener('click', () => {
  const statusDiv = document.getElementById('status');

  // Remove the 'cartUnlockedUntil' timestamp from browser storage
  chrome.storage.local.remove('cartUnlockedUntil', () => {
    statusDiv.style.color = "#ff4757"; // Red color
    statusDiv.innerText = "Cart LOCKED. Refresh the Amazon page.";
  });
});