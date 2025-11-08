// Test workstation matching logic
const fetch = require('node-fetch');

async function test() {
    // Fetch actual data
    const response = await fetch('http://127.0.0.1:3003/api/by-workstation');
    const workstationData = await response.json();

    console.log('=== API Data ===');
    console.log(`Total workstations: ${workstationData.length}`);

    // Simulate the frontend logic
    const selectedWorkstations = new Set();

    // This is what createWorkstationFilters does
    workstationData.forEach(workstation => {
        console.log(`\nWorkstation ID: "${workstation.workstation_id}"`);
        console.log(`  Type: ${typeof workstation.workstation_id}`);
        console.log(`  Length: ${workstation.workstation_id.length}`);
        console.log(`  Has history: ${workstation.history.length} days`);

        // Add to selected set
        selectedWorkstations.add(workstation.workstation_id);
    });

    console.log('\n=== Selected Workstations Set ===');
    console.log(Array.from(selectedWorkstations));

    // Simulate processSelectedData
    console.log('\n=== Processing Data ===');
    const dayMap = new Map();

    workstationData.forEach(ws => {
        console.log(`\nProcessing: "${ws.workstation_id}"`);
        console.log(`  Is in selectedWorkstations? ${selectedWorkstations.has(ws.workstation_id)}`);

        if (!selectedWorkstations.has(ws.workstation_id)) {
            console.log('  SKIPPED - not in selected set');
            return;
        }

        ws.history.forEach(day => {
            if (!dayMap.has(day.day)) {
                dayMap.set(day.day, new Map());
            }
            dayMap.get(day.day).set(ws.workstation_id, day);
        });
    });

    console.log(`\n=== Results ===`);
    console.log(`Total days in dayMap: ${dayMap.size}`);

    // Convert to array
    const processedData = [];
    for (const [day, workstations] of dayMap.entries()) {
        const dayData = { day, workstations: {} };
        for (const [wsId, data] of workstations.entries()) {
            dayData.workstations[wsId] = data;
        }
        processedData.push(dayData);
    }

    console.log(`Processed data length: ${processedData.length}`);
    if (processedData.length > 0) {
        console.log('\nFirst day sample:');
        console.log(JSON.stringify(processedData[0], null, 2));
    }
}

test().catch(console.error);