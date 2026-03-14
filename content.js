// This logs to the console so we know the script is injected
console.log("Cart Defender is active on this page. Monitoring behavior...");

// Let's track how many times they click the mouse
let clickCount = 0;

document.addEventListener('click', (event) => {
    clickCount++;
    console.log(`User clicked! Total clicks this session: ${clickCount}`);
    
    // In the future, this is where we will check if they clicked a "Checkout" button!
});