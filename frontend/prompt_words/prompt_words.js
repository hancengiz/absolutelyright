// Display configuration (loaded from config file)
let DISPLAY_CONFIG = null;

// Track which words are active in the chart
let activeWords = {};

// Check if we should show unfiltered words
const urlParams = new URLSearchParams(window.location.search);
const showUnfiltered = urlParams.get('unfiltered') === 'true';

async function loadDisplayConfig() {
	try {
		const res = await fetch("/prompt_words/words_config.json");
		DISPLAY_CONFIG = await res.json();

		// If unfiltered mode, replace labels with actual word names for merged words
		if (showUnfiltered && DISPLAY_CONFIG.chart?.merge_into_filtered) {
			DISPLAY_CONFIG.chart.merge_into_filtered.forEach(word => {
				if (!DISPLAY_CONFIG.chart.labels[word]) {
					// Capitalize first letter for display
					DISPLAY_CONFIG.chart.labels[word] = word.charAt(0).toUpperCase() + word.slice(1);
				}
			});
		}

		// Initialize activeWords based on tracked words
		const trackedWords = DISPLAY_CONFIG.chart?.tracked_words || [];
		trackedWords.forEach(word => {
			activeWords[word] = true;
		});
		// In filtered mode, also add "filtered" as active
		if (!showUnfiltered) {
			activeWords['filtered'] = true;
		}
	} catch (error) {
		console.error("Error loading display config:", error);
		// Use defaults if config fails to load
		DISPLAY_CONFIG = {
			title: { primary_word: "please", show_this_week: true },
			subtitle: { show_word: "help" },
			chart: {
				words: ["please", "help", "thanks", "fix", "filtered"],
				labels: {
					"please": "Please",
					"help": "Help me",
					"thanks": "Thank you",
					"fix": "Fix this",
					"filtered": "Frustrated"
				},
				colors: ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#E63946"]
			}
		};
	}
}

function generateLegend() {
	const legendContainer = document.getElementById("chart-legend");
	if (!legendContainer || !DISPLAY_CONFIG) return;

	// Build words list: tracked_words + "filtered" if in filtered mode
	let words = [...(DISPLAY_CONFIG.chart?.tracked_words || [])];
	if (!showUnfiltered && DISPLAY_CONFIG.chart?.merge_into_filtered) {
		// Remove words that will be merged, add "filtered" instead
		words = words.filter(w => !DISPLAY_CONFIG.chart.merge_into_filtered.includes(w));
		words.push('filtered');
	}

	const labels = DISPLAY_CONFIG.chart?.labels || {};
	const colors = DISPLAY_CONFIG.chart?.colors || [];

	// Find and clone the "Total user messages" legend item to keep it at the end
	const legendItems = legendContainer.querySelectorAll('.legend-item');
	let totalMessagesClone = null;
	legendItems.forEach(item => {
		if (item.textContent.includes('Total user messages')) {
			totalMessagesClone = item.cloneNode(true);
		}
	});

	// Clear the legend
	legendContainer.innerHTML = '';

	// Add legend items for each word
	words.forEach((word, index) => {
		const legendItem = document.createElement('span');
		legendItem.className = 'legend-item';
		legendItem.style.cursor = 'pointer';

		// Add disabled class if word is not active
		if (!activeWords[word]) {
			legendItem.classList.add('disabled');
		}

		const legendColor = document.createElement('span');
		legendColor.className = 'legend-color';
		legendColor.style.background = colors[index] || '#ccc';

		const label = labels[word] || (word.charAt(0).toUpperCase() + word.slice(1));

		legendItem.appendChild(legendColor);
		legendItem.appendChild(document.createTextNode(' ' + label));

		// Add click handler to toggle word visibility
		legendItem.addEventListener('click', () => {
			activeWords[word] = !activeWords[word];

			// Update legend visual state
			if (activeWords[word]) {
				legendItem.classList.remove('disabled');
			} else {
				legendItem.classList.add('disabled');
			}

			// Redraw chart with new active words
			if (currentHistory.length > 0) {
				drawChart(currentHistory);
			}
		});

		// Add double-click handler to select only this word
		legendItem.addEventListener('dblclick', () => {
			// Deselect all words
			words.forEach(w => {
				activeWords[w] = false;
			});

			// Select only the double-clicked word
			activeWords[word] = true;

			// Update all legend items' visual states
			const allLegendItems = legendContainer.querySelectorAll('.legend-item');
			allLegendItems.forEach((item, idx) => {
				if (idx < words.length) {
					const itemWord = words[idx];
					if (activeWords[itemWord]) {
						item.classList.remove('disabled');
					} else {
						item.classList.add('disabled');
					}
				}
			});

			// Redraw chart with new active words
			if (currentHistory.length > 0) {
				drawChart(currentHistory);
			}
		});

		legendContainer.appendChild(legendItem);
	});

	// Add the total messages item back at the end
	if (totalMessagesClone) {
		legendContainer.appendChild(totalMessagesClone);
	}
}

function getWeekStart(date) {
	const d = new Date(date);
	const day = d.getDay();
	const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
	return new Date(d.setDate(diff)).toISOString().split("T")[0];
}

async function fetchToday(animate = false) {
	try {
		const res = await fetch("/api/prompt-words/today");
		const data = await res.json();
		const countElement = document.getElementById("today-inline");
		const subtitleElement = document.querySelector(".subtitle");
		const secondaryCountElement = document.getElementById("secondary-count");
		const weekCountElement = document.getElementById("week-count");
		const tertiaryCountElement = document.getElementById("tertiary-count");

		// Get primary word count (just "please")
		const primaryWord = DISPLAY_CONFIG?.title?.primary_word || "please";
		const primaryCount = data[primaryWord] || 0;

		// Calculate this week's count if enabled
		if (DISPLAY_CONFIG?.title?.show_this_week && weekCountElement) {
			const historyRes = await fetch("/api/prompt-words/history");
			const history = await historyRes.json();
			const today = new Date().toISOString().split("T")[0];
			const weekStart = getWeekStart(today);

			const weekCount = history
				.filter(d => d.day >= weekStart && d.day <= today)
				.reduce((sum, d) => sum + (d[primaryWord] || 0), 0);

			weekCountElement.textContent = ` (${weekCount} this week)`;
			weekCountElement.style.display = "inline";
		}

		// Show subtitle word count from config (help)
		const subtitleWord = DISPLAY_CONFIG?.subtitle?.show_word || "help";
		const subtitleCount = data[subtitleWord] || 0;
		const subtitleTemplate = DISPLAY_CONFIG?.subtitle?.text_template || `(asked for ${subtitleWord} {count} times)`;

		if (subtitleCount > 0) {
			secondaryCountElement.textContent = subtitleTemplate.replace('{count}', subtitleCount);
			secondaryCountElement.style.display = "block";
		} else {
			secondaryCountElement.style.display = "none";
		}

		// Show tertiary count (frustrated words: fuck, stupid, idiot, shit)
		if (DISPLAY_CONFIG?.tertiary && tertiaryCountElement) {
			const tertiaryWords = DISPLAY_CONFIG.tertiary.show_words || [];
			const tertiaryCount = tertiaryWords.reduce((sum, word) => sum + (data[word] || 0), 0);
			const tertiaryTemplate = DISPLAY_CONFIG.tertiary.text_template || "(got frustrated {count} times)";

			if (tertiaryCount > 0) {
				tertiaryCountElement.textContent = tertiaryTemplate.replace('{count}', tertiaryCount);
				tertiaryCountElement.style.display = "block";
			} else {
				tertiaryCountElement.style.display = "none";
			}
		}

		if (animate && primaryCount > 0) {
			// Show count - 1 first
			countElement.textContent = primaryCount - 1;

			// Fade in the subtitle
			subtitleElement.style.transition = "opacity 0.5s ease-in";
			subtitleElement.style.opacity = "1";

			// After a second, animate to the real count
			setTimeout(() => {
				countElement.style.transform = "scale(1.3)";
				countElement.style.color = "#e63946";
				countElement.textContent = primaryCount;

				// Reset the scale
				setTimeout(() => {
					countElement.style.transform = "";
				}, 300);
			}, 1000);
		} else {
			countElement.textContent = primaryCount;
			// Fade in for non-animated load
			subtitleElement.style.transition = "opacity 0.5s ease-in";
			subtitleElement.style.opacity = "1";
		}
	} catch (error) {
		console.error("Error fetching today:", error);
	}
}

function aggregateSensitiveWords(data) {
	// Combine words into 'filtered' category if not in unfiltered mode
	if (showUnfiltered || !DISPLAY_CONFIG?.chart?.merge_into_filtered) {
		return data;
	}

	const wordsToMerge = DISPLAY_CONFIG.chart.merge_into_filtered;
	return data.map(day => {
		const newDay = { ...day };

		// Sum up all words to merge into 'filtered'
		let filteredSum = 0;
		wordsToMerge.forEach(word => {
			filteredSum += (newDay[word] || 0);
			delete newDay[word]; // Remove individual word
		});

		// Add combined count as 'filtered'
		newDay.filtered = filteredSum;

		return newDay;
	});
}

async function fetchHistory() {
	try {
		const res = await fetch("/api/prompt-words/history");
		let history = await res.json();

		// Add today if it's not in the history
		const today = new Date().toISOString().split("T")[0];
		const hasToday = history.some((d) => d.day === today);

		if (!hasToday) {
			// Fetch today's count to add to the chart
			const todayRes = await fetch("/api/prompt-words/today");
			const todayData = await todayRes.json();

			// Build today's entry with all words
			const todayEntry = { day: today };
			Object.keys(todayData).forEach(key => {
				todayEntry[key] = todayData[key] || 0;
			});

			history.push(todayEntry);

			// Sort by date to ensure chronological order
			history.sort((a, b) => a.day.localeCompare(b.day));
		}

		// Aggregate sensitive words in filtered mode
		history = aggregateSensitiveWords(history);

		currentHistory = history; // Store for resize
		drawChart(history);
	} catch (error) {
		console.error("Error fetching history:", error);
	}
}

function drawChart(history) {
	const chartElement = document.getElementById("chart");
	chartElement.innerHTML = "";

	if (history.length === 0) return;

	// Make chart dimensions responsive
	const isMobile = window.innerWidth <= 600;
	const containerWidth = Math.min(window.innerWidth - 40, 760);
	const width = containerWidth;
	const height = isMobile ? 300 : 350;
	const margin = isMobile
		? { top: 20, right: 10, bottom: 60, left: 40 }
		: { top: 30, right: 20, bottom: 70, left: 80 };

	// Create container div for roughViz
	const container = document.createElement('div');
	container.id = 'chart-container';
	chartElement.appendChild(container);

	// On mobile, show only last 5 days
	const displayHistory = isMobile && history.length > 5
		? history.slice(-5)
		: history;

	// Get all unique words from history (excluding total_user_messages and day)
	const allWords = new Set();
	displayHistory.forEach(d => {
		Object.keys(d).forEach(key => {
			if (key !== 'day' && key !== 'total_user_messages') {
				allWords.add(key);
			}
		});
	});

	// Get word labels and colors from config
	let configWords = [...(DISPLAY_CONFIG?.chart?.tracked_words || Array.from(allWords))];

	// In filtered mode, exclude individual words that are merged, add 'filtered' instead
	if (!showUnfiltered && DISPLAY_CONFIG?.chart?.merge_into_filtered) {
		configWords = configWords.filter(word => !DISPLAY_CONFIG.chart.merge_into_filtered.includes(word));
		configWords.push('filtered');
	}
	const configLabels = DISPLAY_CONFIG?.chart?.labels || {};
	const configColors = DISPLAY_CONFIG?.chart?.colors || ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#E63946'];

	// Filter to only include active words
	const activeWordsFiltered = configWords.filter(word => activeWords[word]);

	// Only show words that have data
	const wordsWithData = activeWordsFiltered.filter(word => {
		return displayHistory.some(d => (d[word] || 0) > 0);
	});
	const wordsToShow = wordsWithData.length > 0 ? wordsWithData : activeWordsFiltered;

	// Format word names using config labels
	const formatWordName = (name) => {
		return configLabels[name] || (name.charAt(0).toUpperCase() + name.slice(1));
	};

	// Create array of {word, label, color} and sort by label alphabetically
	// This ensures colors match the order roughViz uses internally
	const wordData = wordsToShow.map(word => {
		const index = configWords.indexOf(word);
		return {
			word: word,
			label: formatWordName(word),
			color: index >= 0 ? configColors[index] : '#ccc'
		};
	}).sort((a, b) => a.label.localeCompare(b.label));

	// Extract sorted words and colors
	const sortedWordsToShow = wordData.map(wd => wd.word);
	const activeColors = wordData.map(wd => wd.color);

	// Prepare data in the format roughViz expects for stacked bars
	const data = displayHistory.map((d) => {
		const date = new Date(d.day);
		// Show simplified labels on mobile since we have fewer bars
		const label = isMobile
			? date.toLocaleDateString("en-US", { month: "numeric", day: "numeric" })
			: date.toLocaleDateString("en-US", { month: "short", day: "numeric" });

		const row = { date: label };
		// Add each word in sorted order (by label) to match color order
		sortedWordsToShow.forEach(word => {
			row[formatWordName(word)] = d[word] || 0;
		});
		return row;
	});

	if (typeof roughViz === 'undefined') {
		console.error('roughViz library not loaded!');
		return;
	}

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
		yLabel: isMobile ? '' : 'Word Count',
		interactive: true,
		tooltipFontSize: '0.95rem',
		margin: margin,
		axisFontSize: isMobile ? '10' : '12',
		axisStrokeWidth: isMobile ? 1 : 1.5,
		strokeWidth: isMobile ? 1.5 : 2,
	});

	// Hide every other x-axis label to reduce crowding
	setTimeout(() => {
		const xAxisLabels = chartElement.querySelectorAll('.x-axis text, .xAxis text, svg text');
		xAxisLabels.forEach((label, i) => {
			if (i % 2 === 1) {
				label.style.opacity = '0';
			}
		});

		// Add total user messages line
		addTotalUserMessagesLine(chartElement, displayHistory, isMobile, width, height, margin);

		// Enhance tooltips to show word names (use sorted words for consistency)
		enhanceTooltips(chartElement, displayHistory, sortedWordsToShow, configLabels);
	}, 100);
}

function addTotalUserMessagesLine(chartElement, displayHistory, isMobile, width, height, margin) {
	const svg = chartElement.querySelector('svg');
	if (!svg) return;

	// Get actual SVG dimensions from viewBox
	const viewBox = svg.getAttribute('viewBox');
	const [, , vbWidth, vbHeight] = viewBox ? viewBox.trim().split(/\s+/).map(Number) : [0, 0, width, height];

	const chartWidth = vbWidth - margin.left - margin.right;
	const chartHeight = vbHeight - margin.top - margin.bottom;

	// Find all rect elements (bars) to determine x positions and bar widths
	const rects = Array.from(svg.querySelectorAll('rect'));
	const barGroups = new Map();
	rects.forEach(rect => {
		const x = parseFloat(rect.getAttribute('x'));
		if (!barGroups.has(x)) {
			barGroups.set(x, []);
		}
		barGroups.get(x).push(rect);
	});

	const sortedXPositions = Array.from(barGroups.keys()).sort((a, b) => a - b);

	// Find the main chart group
	const groups = svg.querySelectorAll('g');
	const chartGroup = Array.from(groups).find(g => {
		const t = g.getAttribute('transform');
		return t && t.includes(`translate(${margin.left}`) && t.includes(`${margin.top})`);
	});

	if (!chartGroup) return;

	// Calculate min and max total user messages for square root scaling
	const totalMessagesValues = displayHistory.map(d => d.total_user_messages || 0).filter(v => v > 0);
	if (totalMessagesValues.length === 0) return;

	const minTotalMessages = Math.min(...totalMessagesValues, 1);
	const maxTotalMessages = Math.max(...totalMessagesValues, 1);
	const sqrtMin = Math.sqrt(minTotalMessages);
	const sqrtMax = Math.sqrt(maxTotalMessages);
	const sqrtRange = sqrtMax - sqrtMin || 1;

	// Ensure chart element is positioned relatively for absolute tooltips
	if (!chartElement.style.position || chartElement.style.position === 'static') {
		chartElement.style.position = 'relative';
	}

	// Create or reuse tooltip element
	let tooltip = chartElement.querySelector('.totals-tooltip');
	if (!tooltip) {
		tooltip = document.createElement('div');
		tooltip.className = 'totals-tooltip';
		tooltip.style.cssText = 'position: absolute; padding: 0.5rem; font-size: 0.95rem; line-height: 1rem; opacity: 0; pointer-events: none; font-family: Gaegu, cursive; z-index: 10000; color: #374151; background: rgba(255, 255, 255, 0.9); border-radius: 4px;';
		chartElement.appendChild(tooltip);
	}

	// Calculate line points for total user messages
	const linePoints = displayHistory.map((d, originalIndex) => {
		const totalMsgs = d.total_user_messages || 0;

		// Get x position (center of bar) using originalIndex
		let xPosition;
		if (sortedXPositions[originalIndex] !== undefined) {
			const targetX = sortedXPositions[originalIndex];
			const targetRects = barGroups.get(targetX);
			const barWidth = targetRects[0] ? parseFloat(targetRects[0].getAttribute('width')) : chartWidth / displayHistory.length * 0.6;
			xPosition = targetX + barWidth / 2;
		} else {
			// Fallback calculation
			const barWidth = chartWidth / displayHistory.length;
			xPosition = (originalIndex * barWidth) + (barWidth / 2);
		}

		// Square root scale: map sqrt(min)-sqrt(max) range to 10%-100% of chart height
		const sqrtValue = Math.sqrt(totalMsgs);
		const normalizedValue = (sqrtValue - sqrtMin) / sqrtRange;
		const yPosition = chartHeight - (0.1 + normalizedValue * 0.9) * chartHeight;

		return { x: xPosition, y: yPosition, value: totalMsgs, originalIndex };
	});

	// Draw hand-drawn style line using rough.js
	if (typeof rough !== 'undefined' && linePoints.length > 1) {
		// Filter out any invalid points
		const validPoints = linePoints.filter(p =>
			!isNaN(p.x) && !isNaN(p.y) && isFinite(p.x) && isFinite(p.y) && p.value > 0
		);

		if (validPoints.length > 0) {
			const rc = rough.svg(svg);

			// Create path data for the line
			const points = validPoints.map(p => [p.x, p.y]);

			// Draw rough linearPath
			const roughPath = rc.linearPath(points, {
				stroke: '#c0c4ca',
				strokeWidth: isMobile ? 2.5 : 3,
				roughness: 1.5,
				bowing: 1
			});

			// Set opacity and class for toggling
			roughPath.setAttribute('opacity', '0.6');
			roughPath.classList.add('total-line');
			roughPath.style.display = totalLineVisible ? 'block' : 'none';

			// Insert line at the beginning so it's behind the main bars
			chartGroup.insertBefore(roughPath, chartGroup.firstChild);
		}
	}

	// Draw circles at each point with tooltips
	linePoints.forEach((p) => {
		if (p.value > 0) {
			const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
			circle.setAttribute('cx', p.x);
			circle.setAttribute('cy', p.y);
			circle.setAttribute('r', isMobile ? '3' : '3.5');
			circle.setAttribute('fill', '#c0c4ca');
			circle.setAttribute('stroke', 'white');
			circle.setAttribute('stroke-width', '1.5');
			circle.setAttribute('opacity', '0.9');
			circle.style.cursor = 'pointer';
			circle.classList.add('total-line');
			circle.style.display = totalLineVisible ? 'block' : 'none';

			// Add tooltip
			circle.addEventListener('mouseenter', (e) => {
				tooltip.textContent = '';

				const date = new Date(displayHistory[p.originalIndex].day);
				const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
				tooltip.appendChild(document.createTextNode(dateStr + ': '));

				const bold = document.createElement('b');
				bold.textContent = p.value.toString();
				tooltip.appendChild(bold);
				tooltip.appendChild(document.createTextNode(' user messages'));

				tooltip.style.display = 'block';
				tooltip.style.opacity = '1';

				const chartRect = chartElement.getBoundingClientRect();
				tooltip.style.left = (e.clientX - chartRect.left + 10) + 'px';
				tooltip.style.top = (e.clientY - chartRect.top - 30) + 'px';
			});

			circle.addEventListener('mousemove', (e) => {
				const chartRect = chartElement.getBoundingClientRect();
				tooltip.style.left = (e.clientX - chartRect.left + 10) + 'px';
				tooltip.style.top = (e.clientY - chartRect.top - 30) + 'px';
			});

			circle.addEventListener('mouseleave', () => {
				tooltip.style.opacity = '0';
				tooltip.style.display = 'none';
			});

			chartGroup.appendChild(circle);
		}
	});
}

function enhanceTooltips(chartElement, displayHistory, wordsToShow, labels) {
	const svg = chartElement.querySelector('svg');
	if (!svg) return;

	// Ensure chart element is positioned for absolute tooltips
	chartElement.style.position = 'relative';

	// Create custom tooltip element
	let customTooltip = chartElement.querySelector('.custom-tooltip');
	if (!customTooltip) {
		customTooltip = document.createElement('div');
		customTooltip.className = 'custom-tooltip';
		customTooltip.style.cssText = 'position: absolute; padding: 0.75rem; font-size: 0.95rem; opacity: 0; pointer-events: none; font-family: Gaegu, cursive; z-index: 10000; background: white; border: 2px solid #333; border-radius: 6px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: opacity 0.15s;';
		chartElement.appendChild(customTooltip);
	}

	// Find all path elements (roughViz uses paths for bars)
	const paths = Array.from(svg.querySelectorAll('path'));

	// Also try rects as fallback
	const rects = Array.from(svg.querySelectorAll('rect'));

	const elements = [...paths, ...rects].filter(el => {
		// Filter out axes and other non-bar elements
		const fill = el.getAttribute('fill');
		return fill && fill !== 'none' && !fill.includes('url(');
	});

	// Group by x position
	const barGroups = new Map();
	elements.forEach(el => {
		const bbox = el.getBBox();
		const x = Math.round(bbox.x);
		if (!barGroups.has(x)) {
			barGroups.set(x, []);
		}
		barGroups.get(x).push(el);
	});

	// For each bar group, add tooltip handlers
	let groupIndex = 0;
	barGroups.forEach((bars) => {
		if (groupIndex >= displayHistory.length) return;

		const dayData = displayHistory[groupIndex];
		groupIndex++;

		bars.forEach(el => {
			el.style.cursor = 'pointer';

			el.addEventListener('mouseenter', (e) => {
				// Build tooltip content with word breakdown
				const date = new Date(dayData.day);
				const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });

				let tooltipHTML = `<div style="font-weight: bold; margin-bottom: 0.5rem; color: #1f2937;">${dateStr}</div>`;

				wordsToShow.forEach(word => {
					const count = dayData[word] || 0;
					const label = labels[word] || (word.charAt(0).toUpperCase() + word.slice(1));
					if (count > 0) {
						tooltipHTML += `<div style="margin: 0.25rem 0;"><b>${label}:</b> ${count}</div>`;
					}
				});

				// Add total messages
				const totalMessages = dayData.total_user_messages || 0;
				if (totalMessages > 0) {
					tooltipHTML += `<div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #e5e7eb; color: #6b7280;"><b>Total messages:</b> ${totalMessages}</div>`;
				}

				customTooltip.innerHTML = tooltipHTML;
				customTooltip.style.opacity = '1';
				customTooltip.style.display = 'block';

				const chartRect = chartElement.getBoundingClientRect();
				customTooltip.style.left = (e.clientX - chartRect.left + 10) + 'px';
				customTooltip.style.top = (e.clientY - chartRect.top - 10) + 'px';
			});

			el.addEventListener('mousemove', (e) => {
				const chartRect = chartElement.getBoundingClientRect();
				customTooltip.style.left = (e.clientX - chartRect.left + 10) + 'px';
				customTooltip.style.top = (e.clientY - chartRect.top - 10) + 'px';
			});

			el.addEventListener('mouseleave', () => {
				customTooltip.style.opacity = '0';
				setTimeout(() => {
					if (customTooltip.style.opacity === '0') {
						customTooltip.style.display = 'none';
					}
				}, 200);
			});
		});
	});
}

// Store history globally for redraw
let currentHistory = [];

// Track visibility of total line
let totalLineVisible = true;

// Load rough.js library first, then roughViz
const roughScript = document.createElement('script');
roughScript.src = 'https://unpkg.com/roughjs@4.5.2/bundled/rough.js';
roughScript.onload = () => {
	// Then load roughViz library
	const script = document.createElement('script');
	script.src = 'https://unpkg.com/rough-viz@2.0.5';
	script.onload = async () => {
		// Load display config first
		await loadDisplayConfig();

		// Generate legend from config
		generateLegend();

		// Show unfiltered notice if in unfiltered mode
		if (showUnfiltered) {
			document.getElementById('unfiltered-notice').style.display = 'block';
		}

		// Initial load with animation
		fetchToday(true);
		fetchHistory().then(() => {
			// Initialize total line legend toggle
			const legendItems = document.querySelectorAll('.legend-item');
			// Find the total user messages legend item (last item)
			const totalLegendItem = legendItems[legendItems.length - 1];

			if (totalLegendItem) {
				totalLegendItem.style.cursor = 'pointer';
				totalLegendItem.addEventListener('click', () => {
					// Toggle visibility
					totalLineVisible = !totalLineVisible;

					// Update legend visual state
					if (totalLineVisible) {
						totalLegendItem.classList.remove('disabled');
					} else {
						totalLegendItem.classList.add('disabled');
					}

					// Toggle all total line elements
					const totalElements = document.querySelectorAll('.total-line');
					totalElements.forEach(el => {
						el.style.display = totalLineVisible ? 'block' : 'none';
					});
				});
			}

			// Redraw chart on window resize
			let resizeTimeout;
			window.addEventListener("resize", () => {
				clearTimeout(resizeTimeout);
				resizeTimeout = setTimeout(() => {
					if (currentHistory.length > 0) {
						drawChart(currentHistory);
					}
				}, 250);
			});
		});
	};
	document.head.appendChild(script);
};
document.head.appendChild(roughScript);

// Refresh every 5 seconds (without animation)
setInterval(() => fetchToday(false), 5000);
