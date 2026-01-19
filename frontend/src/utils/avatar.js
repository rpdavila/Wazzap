/**
 * Generate a hybrid identicon/shape avatar based on an ID
 * @param {number|string} id - The ID to generate avatar for (chat ID or user ID)
 * @param {number} size - Size of the avatar in pixels (default: 40)
 * @returns {string} SVG data URL
 */
export function generateAvatar(id, size = 40) {
  // Convert ID to a seed for deterministic randomness
  const seed = typeof id === 'string' ? hashString(id) : id;
  
  // Use a simple seeded random number generator
  let rng = seedRandom(seed);
  
  // Simple color palette - 2-3 colors max
  const colorPalette = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#98D8C8', '#F7DC6F',
    '#BB8FCE', '#85C1E2', '#2ECC71', '#9B59B6', '#1ABC9C'
  ];
  
  // Select 2-3 colors
  const numColors = Math.floor(rng() * 2) + 2; // 2-3 colors
  const selectedColors = [];
  const usedIndices = new Set();
  
  for (let i = 0; i < numColors; i++) {
    let index;
    do {
      index = Math.floor(rng() * colorPalette.length);
    } while (usedIndices.has(index));
    usedIndices.add(index);
    selectedColors.push(colorPalette[index]);
  }
  
  // Decide on style: identicon grid or geometric shapes (or mix)
  const style = Math.floor(rng() * 3); // 0=identicon, 1=shapes, 2=mixed
  
  const elements = [];
  
  if (style === 0) {
    // Pure identicon - grid pattern
    const gridSize = 5; // 5x5 grid
    const cellSize = size / gridSize;
    const primaryColor = selectedColors[0];
    const secondaryColor = selectedColors[1] || selectedColors[0];
    
    // Create symmetric identicon pattern
    for (let row = 0; row < gridSize; row++) {
      for (let col = 0; col < Math.ceil(gridSize / 2); col++) {
        const shouldFill = Math.floor(rng() * 2) === 1;
        if (shouldFill) {
          const color = Math.floor(rng() * 2) === 0 ? primaryColor : secondaryColor;
          // Left side
          elements.push(`<rect x="${col * cellSize}" y="${row * cellSize}" width="${cellSize}" height="${cellSize}" fill="${color}"/>`);
          // Right side (mirror)
          if (col < Math.floor(gridSize / 2)) {
            elements.push(`<rect x="${(gridSize - 1 - col) * cellSize}" y="${row * cellSize}" width="${cellSize}" height="${cellSize}" fill="${color}"/>`);
          }
        }
      }
    }
  } else if (style === 1) {
    // Pure geometric shapes with collision detection
    const numShapes = numColors;
    const placedShapes = []; // Track placed shapes to avoid overlaps
    
    // Helper function to check if two shapes overlap
    function shapesOverlap(shape1, shape2) {
      const minDistance = (shape1.size + shape2.size) * 0.8; // 80% of combined size
      const dx = shape1.cx - shape2.cx;
      const dy = shape1.cy - shape2.cy;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return distance < minDistance;
    }
    
    // Helper to find a non-overlapping position
    function findPosition(shapeSize, maxAttempts = 20) {
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const cx = size * (0.25 + rng() * 0.5); // Keep shapes more centered
        const cy = size * (0.25 + rng() * 0.5);
        
        const newShape = { cx, cy, size: shapeSize };
        const overlaps = placedShapes.some(placed => shapesOverlap(newShape, placed));
        
        if (!overlaps) {
          return { cx, cy };
        }
      }
      // If we can't find a good position, use a corner
      const corners = [
        { cx: size * 0.3, cy: size * 0.3 },
        { cx: size * 0.7, cy: size * 0.3 },
        { cx: size * 0.3, cy: size * 0.7 },
        { cx: size * 0.7, cy: size * 0.7 }
      ];
      return corners[placedShapes.length % corners.length];
    }
    
    for (let i = 0; i < numShapes; i++) {
      const color = selectedColors[i];
      const shapeType = Math.floor(rng() * 3); // 0=circle, 1=rectangle, 2=triangle
      const baseSize = size * (0.12 + rng() * 0.15); // Smaller sizes to reduce overlap
      
      const pos = findPosition(baseSize);
      const cx = pos.cx;
      const cy = pos.cy;
      
      // Track this shape
      placedShapes.push({ cx, cy, size: baseSize });
      
      const rotation = shapeType === 1 ? rng() * 45 : 0;
      
      if (shapeType === 0) {
        elements.push(`<circle cx="${cx}" cy="${cy}" r="${baseSize}" fill="${color}"/>`);
      } else if (shapeType === 1) {
        const halfSize = baseSize;
        elements.push(`<rect x="${cx - halfSize}" y="${cy - halfSize}" width="${halfSize * 2}" height="${halfSize * 2}" fill="${color}" transform="rotate(${rotation} ${cx} ${cy})"/>`);
      } else {
        const halfSize = baseSize;
        const points = [
          `${cx},${cy - halfSize}`,
          `${cx - halfSize},${cy + halfSize}`,
          `${cx + halfSize},${cy + halfSize}`
        ];
        elements.push(`<polygon points="${points.join(' ')}" fill="${color}"/>`);
      }
    }
  } else {
    // Mixed: identicon grid + geometric shapes
    const gridSize = 4; // Smaller grid for mixed
    const cellSize = size / gridSize;
    const primaryColor = selectedColors[0];
    
    // Add some identicon squares
    for (let row = 0; row < gridSize; row++) {
      for (let col = 0; col < Math.ceil(gridSize / 2); col++) {
        if (Math.floor(rng() * 3) === 0) { // 1/3 chance
          // Left side
          elements.push(`<rect x="${col * cellSize}" y="${row * cellSize}" width="${cellSize}" height="${cellSize}" fill="${primaryColor}"/>`);
          // Right side (mirror)
          if (col < Math.floor(gridSize / 2)) {
            elements.push(`<rect x="${(gridSize - 1 - col) * cellSize}" y="${row * cellSize}" width="${cellSize}" height="${cellSize}" fill="${primaryColor}"/>`);
          }
        }
      }
    }
    
    // Add 1-2 geometric shapes on top with collision detection
    const numShapes = Math.floor(rng() * 2) + 1;
    const placedShapes = [];
    
    // Helper function to check if two shapes overlap
    function shapesOverlap(shape1, shape2) {
      const minDistance = (shape1.size + shape2.size) * 0.8;
      const dx = shape1.cx - shape2.cx;
      const dy = shape1.cy - shape2.cy;
      const distance = Math.sqrt(dx * dx + dy * dy);
      return distance < minDistance;
    }
    
    // Helper to find a non-overlapping position
    function findPosition(shapeSize, maxAttempts = 20) {
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const cx = size * (0.25 + rng() * 0.5);
        const cy = size * (0.25 + rng() * 0.5);
        
        const newShape = { cx, cy, size: shapeSize };
        const overlaps = placedShapes.some(placed => shapesOverlap(newShape, placed));
        
        if (!overlaps) {
          return { cx, cy };
        }
      }
      // Fallback to corners
      const corners = [
        { cx: size * 0.3, cy: size * 0.3 },
        { cx: size * 0.7, cy: size * 0.7 }
      ];
      return corners[placedShapes.length % corners.length];
    }
    
    for (let i = 0; i < numShapes; i++) {
      const color = selectedColors[i + 1] || selectedColors[0];
      const shapeType = Math.floor(rng() * 3);
      const baseSize = size * (0.1 + rng() * 0.15); // Smaller to avoid blocking grid
      
      const pos = findPosition(baseSize);
      const cx = pos.cx;
      const cy = pos.cy;
      
      // Track this shape
      placedShapes.push({ cx, cy, size: baseSize });
      
      if (shapeType === 0) {
        elements.push(`<circle cx="${cx}" cy="${cy}" r="${baseSize}" fill="${color}"/>`);
      } else if (shapeType === 1) {
        const halfSize = baseSize;
        const rotation = rng() * 45;
        elements.push(`<rect x="${cx - halfSize}" y="${cy - halfSize}" width="${halfSize * 2}" height="${halfSize * 2}" fill="${color}" transform="rotate(${rotation} ${cx} ${cy})"/>`);
      } else {
        const halfSize = baseSize;
        const points = [
          `${cx},${cy - halfSize}`,
          `${cx - halfSize},${cy + halfSize}`,
          `${cx + halfSize},${cy + halfSize}`
        ];
        elements.push(`<polygon points="${points.join(' ')}" fill="${color}"/>`);
      }
    }
  }
  
  const svg = `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">${elements.join('')}</svg>`;
  
  // Convert to data URL
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

/**
 * Simple hash function for strings
 */
function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
}

/**
 * Seeded random number generator
 */
function seedRandom(seed) {
  let value = seed;
  return function() {
    value = (value * 9301 + 49297) % 233280;
    return value / 233280;
  };
}
