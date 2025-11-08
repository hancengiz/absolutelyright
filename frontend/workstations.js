// RoughViz is included inline in the HTML via CDN or embedded in the page

// Global configuration
const API_BASE = '';  // Will use relative paths
const PATTERN_COLORS = {
  absolutely: '#ef4444',  // red
  right: '#3b82f6',       // blue
  perfect: '#10b981',     // green
  excellent: '#f59e0b',   // amber
};

const PATTERN_LABELS = {
  absolutely: 'Absolutely/Completely right',
  right: 'Right',
  perfect: 'Perfect!',
  excellent: 'Excellent!',
};

let workstationData = [];
let selectedWorkstations = new Set();
// Match main page default: only 'absolutely' and 'right' enabled by default
let visiblePatterns = new Set(['absolutely', 'right']);

// Fetch data from API
async function fetchWorkstationData() {
  try {
    const response = await fetch(`${API_BASE}/api/by-workstation`);
    if (!response.ok) throw new Error('Failed to fetch data');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching data:', error);
    return [];
  }
}

// Create workstation filter checkboxes
function createWorkstationFilters(data) {
  const filterContainer = document.getElementById('workstation-filter');

  // Clear existing checkboxes (keep title)
  const title = filterContainer.querySelector('.workstation-filter-title');
  filterContainer.innerHTML = '';
  filterContainer.appendChild(title);

  data.forEach(workstation => {
    const totalCount = workstation.history.reduce((sum, day) => {
      return sum + (day.absolutely || 0) + (day.right || 0) +
             (day.perfect || 0) + (day.excellent || 0);
    }, 0);

    const checkboxDiv = document.createElement('div');
    checkboxDiv.className = 'workstation-checkbox';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `ws-${workstation.workstation_id}`;
    checkbox.value = workstation.workstation_id;
    checkbox.checked = true;
    selectedWorkstations.add(workstation.workstation_id);

    checkbox.addEventListener('change', (e) => {
      if (e.target.checked) {
        selectedWorkstations.add(workstation.workstation_id);
      } else {
        selectedWorkstations.delete(workstation.workstation_id);
      }
      updateChart();
    });

    const label = document.createElement('label');
    label.htmlFor = `ws-${workstation.workstation_id}`;
    label.className = 'workstation-label';
    label.innerHTML = `${workstation.workstation_id}<span class="workstation-count">(${totalCount} total)</span>`;

    checkboxDiv.appendChild(checkbox);
    checkboxDiv.appendChild(label);
    filterContainer.appendChild(checkboxDiv);
  });
}

// Process data for the selected workstations - aggregate by day
function processSelectedData() {
  // Aggregate data by day for selected workstations
  const dayMap = new Map();

  workstationData.forEach(ws => {
    if (!selectedWorkstations.has(ws.workstation_id)) return;

    ws.history.forEach(day => {
      if (!dayMap.has(day.day)) {
        dayMap.set(day.day, {
          day: day.day,
          absolutely: 0,
          right: 0,
          perfect: 0,
          excellent: 0,
          total_messages: 0
        });
      }

      const aggregated = dayMap.get(day.day);
      aggregated.absolutely += (day.absolutely || 0);
      aggregated.right += (day.right || 0);
      aggregated.perfect += (day.perfect || 0);
      aggregated.excellent += (day.excellent || 0);
      aggregated.total_messages += (day.total_messages || 0);
    });
  });

  // Convert to array and sort by date
  const processedData = Array.from(dayMap.values())
    .sort((a, b) => a.day.localeCompare(b.day));

  return processedData;
}

// Update the chart - using the SAME approach as main page
function updateChart() {
  const chartContainer = document.getElementById('chart');
  const noDataMessage = document.getElementById('no-data-message');

  if (selectedWorkstations.size === 0) {
    chartContainer.style.display = 'none';
    noDataMessage.style.display = 'block';
    return;
  }

  chartContainer.style.display = 'block';
  noDataMessage.style.display = 'none';

  const processedData = processSelectedData();

  if (processedData.length === 0) {
    chartContainer.innerHTML = '<p>No data available for selected workstations</p>';
    return;
  }

  // Clear the chart container
  chartContainer.innerHTML = '';

  // Create container div for roughViz
  const container = document.createElement('div');
  container.id = 'chart-container';
  chartContainer.appendChild(container);

  try {
    // Check if roughViz is loaded
    if (typeof roughViz === 'undefined') {
      console.error('RoughViz library not loaded');
      chartContainer.innerHTML = '<p>Error: Chart library not loaded. Please refresh the page.</p>';
      return;
    }

    // Make chart dimensions responsive (same as main page)
    const isMobile = window.innerWidth <= 600;
    const containerWidth = Math.min(window.innerWidth - 40, 760);
    const width = containerWidth;
    const height = isMobile ? 300 : 350;
    const margin = isMobile
      ? { top: 20, right: 10, bottom: 60, left: 40 }
      : { top: 30, right: 20, bottom: 70, left: 80 };

    // Filter to only include active patterns
    const activePatternsFiltered = Object.keys(PATTERN_COLORS).filter(pattern => visiblePatterns.has(pattern));
    const activeColors = Object.keys(PATTERN_COLORS)
      .filter(pattern => visiblePatterns.has(pattern))
      .map(pattern => PATTERN_COLORS[pattern]);

    // Prepare data in the format roughViz expects for stacked bars (SAME as main page)
    const data = processedData.map((d) => {
      const date = new Date(d.day);
      const label = isMobile
        ? date.toLocaleDateString("en-US", { month: "numeric", day: "numeric" })
        : date.toLocaleDateString("en-US", { month: "short", day: "numeric" });

      const row = { date: label };
      // Add each active pattern
      activePatternsFiltered.forEach(pattern => {
        row[PATTERN_LABELS[pattern]] = d[pattern] || 0;
      });
      return row;
    });

    // Create the chart using StackedBar (SAME as main page)
    new roughViz.StackedBar({
      element: '#chart-container',
      data: data,
      labels: 'date',
      width: width,
      height: height,
      highlight: activeColors,
      roughness: 1.5,
      font: 'Gaegu',
      xLabel: '',
      yLabel: isMobile ? '' : 'Count',
      interactive: true,
      tooltipFontSize: '0.95rem',
      margin: margin,
      axisFontSize: isMobile ? '10' : '12',
      axisStrokeWidth: isMobile ? 1 : 1.5,
      strokeWidth: isMobile ? 1.5 : 2,
    });

    // Hide every other x-axis label to reduce crowding (SAME as main page)
    setTimeout(() => {
      const xAxisLabels = chartContainer.querySelectorAll('.x-axis text, .xAxis text, svg text');
      xAxisLabels.forEach((label, i) => {
        if (i % 2 === 1) {
          label.style.opacity = '0';
        }
      });
    }, 100);

  } catch (error) {
    console.error('Error creating chart:', error);
    chartContainer.innerHTML = '<p>Error creating chart: ' + error.message + '</p>';
  }
}

// Create pattern legend (toggleable)
function createPatternLegend() {
  const legendContainer = document.getElementById('chart-legend');

  // Clear existing legend items except the total messages one
  const existingTotal = legendContainer.querySelector('.legend-item');
  legendContainer.innerHTML = '';

  // Add pattern legend items
  Object.entries(PATTERN_COLORS).forEach(([pattern, color]) => {
    const item = document.createElement('span');
    item.className = 'legend-item';
    item.style.cursor = 'pointer';
    item.dataset.pattern = pattern;

    if (!visiblePatterns.has(pattern)) {
      item.classList.add('disabled');
    }

    const colorBox = document.createElement('span');
    colorBox.className = 'legend-color';
    colorBox.style.background = color;

    const label = document.createTextNode(PATTERN_LABELS[pattern] || pattern);

    item.appendChild(colorBox);
    item.appendChild(document.createTextNode(' '));
    item.appendChild(label);

    item.addEventListener('click', () => {
      if (visiblePatterns.has(pattern)) {
        visiblePatterns.delete(pattern);
        item.classList.add('disabled');
      } else {
        visiblePatterns.add(pattern);
        item.classList.remove('disabled');
      }
      updateChart();
    });

    legendContainer.appendChild(item);
  });

  // Add total messages legend back
  if (existingTotal) {
    legendContainer.appendChild(existingTotal);
  }
}

// Initialize
async function init() {
  console.log('Initializing workstations page...');

  // Fetch data
  workstationData = await fetchWorkstationData();
  console.log(`Fetched data for ${workstationData.length} workstations`);

  if (workstationData.length === 0) {
    document.getElementById('chart').innerHTML = '<p>No data available</p>';
    document.querySelector('.subtitle').style.opacity = '1';
    document.querySelector('.subtitle').textContent = 'No workstation data available';
    return;
  }

  // Create filters
  createWorkstationFilters(workstationData);

  // Create legend
  createPatternLegend();

  // Initial chart render
  updateChart();

  // Show subtitle
  document.querySelector('.subtitle').style.opacity = '1';

  // Update subtitle with workstation count
  const totalWorkstations = workstationData.length;
  document.querySelector('.subtitle').innerHTML =
    `Viewing data from <span class="highlight">${totalWorkstations}</span> workstation${totalWorkstations > 1 ? 's' : ''}`;
}

// Start when DOM is ready AND roughViz is loaded
function waitForLibrariesAndInit() {
  if (typeof roughViz !== 'undefined') {
    // Libraries are loaded, proceed with init
    init();
  } else {
    // Wait a bit and try again
    setTimeout(waitForLibrariesAndInit, 100);
  }
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', waitForLibrariesAndInit);
} else {
  waitForLibrariesAndInit();
}
