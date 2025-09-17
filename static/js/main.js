// Main JavaScript for FoodSave

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Search form enhancement
    const searchForm = document.querySelector('form[action*="search"]');
    if (searchForm) {
        const searchInput = searchForm.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.addEventListener('keyup', debounce(function() {
                // Auto-search functionality can be added here
                console.log('Search query:', this.value);
            }, 300));
        }
    }

    // Add to cart functionality
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function() {
            const offerId = this.dataset.offerId;
            addToCart(offerId, this);
        });
    });

    // Quantity controls
    document.querySelectorAll('.quantity-control').forEach(control => {
        const minusBtn = control.querySelector('.quantity-minus');
        const plusBtn = control.querySelector('.quantity-plus');
        const input = control.querySelector('.quantity-input');

        if (minusBtn && plusBtn && input) {
            minusBtn.addEventListener('click', () => {
                const currentValue = parseInt(input.value) || 1;
                if (currentValue > 1) {
                    input.value = currentValue - 1;
                    input.dispatchEvent(new Event('change'));
                }
            });

            plusBtn.addEventListener('click', () => {
                const currentValue = parseInt(input.value) || 1;
                const maxValue = parseInt(input.getAttribute('max')) || 999;
                if (currentValue < maxValue) {
                    input.value = currentValue + 1;
                    input.dispatchEvent(new Event('change'));
                }
            });
        }
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Image lazy loading
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }

    // Auto-hide alerts
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            if (alert.classList.contains('alert-success')) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);
});

// Compact Catalog Filter and Search Functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeCompactFilters();
    initializeQuickFilters();
    initializeSorting();
    initializeViewToggle();
    updateCartCount();
    calculateDistances();
});

// Compact Filter System
function initializeCompactFilters() {
    const priceRange = document.getElementById('priceRange');
    const minPriceInput = document.getElementById('minPrice');
    const maxPriceInput = document.getElementById('maxPrice');
    const applyFiltersBtn = document.getElementById('applyFilters');
    const clearFiltersBtn = document.getElementById('clearFilters');
    const resetFiltersBtn = document.getElementById('resetFilters');

    // Price range slider
    if (priceRange) {
        priceRange.addEventListener('input', function() {
            maxPriceInput.value = this.value;
        });
    }

    // Apply filters button
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyAllFilters);
    }

    // Clear filters button
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearAllFilters);
    }

    // Reset filters button
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', clearAllFilters);
    }

    // Auto-apply filters on change (with debounce)
    const filterInputs = document.querySelectorAll('.category-filter, .vendor-filter, input[name="distance"]');
    filterInputs.forEach(input => {
        input.addEventListener('change', debounce(applyAllFilters, 300));
    });

    // Price inputs with debounce
    if (minPriceInput && maxPriceInput) {
        minPriceInput.addEventListener('input', debounce(applyAllFilters, 500));
        maxPriceInput.addEventListener('input', debounce(applyAllFilters, 500));
    }
}

// Quick Filter Chips
function initializeQuickFilters() {
    const quickFilters = document.querySelectorAll('input[name="quick-filter"]');
    
    quickFilters.forEach(filter => {
        filter.addEventListener('change', function() {
            if (this.checked) {
                applyQuickFilter(this.id);
            }
        });
    });
}

function applyQuickFilter(filterId) {
    const url = new URL(window.location);
    
    // Clear existing quick filters
    url.searchParams.delete('type');
    url.searchParams.delete('discount');
    
    switch(filterId) {
        case 'filter-dishes':
            url.searchParams.set('type', 'dishes');
            break;
        case 'filter-products':
            url.searchParams.set('type', 'products');
            break;
        case 'filter-discount':
            url.searchParams.set('discount', '20');
            break;
        case 'filter-all':
        default:
            // No additional parameters needed
            break;
    }
    
    window.location.href = url.toString();
}

// Apply all filters function
function applyAllFilters() {
    const url = new URL(window.location);
    
    // Clear existing filter parameters
    url.searchParams.delete('categories');
    url.searchParams.delete('vendors');
    url.searchParams.delete('min_price');
    url.searchParams.delete('max_price');
    url.searchParams.delete('distance');

    // Get selected categories
    const selectedCategories = Array.from(document.querySelectorAll('.category-filter:checked'))
        .map(cb => cb.value);
    selectedCategories.forEach(cat => url.searchParams.append('categories', cat));

    // Get selected vendors
    const selectedVendors = Array.from(document.querySelectorAll('.vendor-filter:checked'))
        .map(cb => cb.value);
    selectedVendors.forEach(vendor => url.searchParams.append('vendors', vendor));

    // Get price range
    const minPrice = document.getElementById('minPrice')?.value;
    const maxPrice = document.getElementById('maxPrice')?.value;
    if (minPrice && minPrice > 0) url.searchParams.set('min_price', minPrice);
    if (maxPrice && maxPrice > 0) url.searchParams.set('max_price', maxPrice);

    // Get selected distance
    const selectedDistance = document.querySelector('input[name="distance"]:checked')?.value;
    if (selectedDistance) url.searchParams.set('distance', selectedDistance);

    // Apply filters with smooth transition
    showLoadingState();
    window.location.href = url.toString();
}

// Clear all filters
function clearAllFilters() {
    // Clear checkboxes
    document.querySelectorAll('.category-filter, .vendor-filter').forEach(cb => cb.checked = false);
    
    // Clear radio buttons
    document.querySelectorAll('input[name="distance"]').forEach(radio => radio.checked = false);
    
    // Clear price inputs
    const minPrice = document.getElementById('minPrice');
    const maxPrice = document.getElementById('maxPrice');
    const priceRange = document.getElementById('priceRange');
    
    if (minPrice) minPrice.value = '';
    if (maxPrice) maxPrice.value = '';
    if (priceRange) priceRange.value = priceRange.max;
    
    // Reset quick filters
    document.getElementById('filter-all').checked = true;
    
    // Redirect to clean catalog
    window.location.href = window.location.pathname;
}

// Sorting functionality
function initializeSorting() {
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            const url = new URL(window.location);
            if (this.value) {
                url.searchParams.set('sort', this.value);
            } else {
                url.searchParams.delete('sort');
            }
            showLoadingState();
            window.location.href = url.toString();
        });

        // Set current sort value
        const urlParams = new URLSearchParams(window.location.search);
        const currentSort = urlParams.get('sort');
        if (currentSort) {
            sortSelect.value = currentSort;
        }
    }
}

// View toggle functionality
function initializeViewToggle() {
    const gridViewBtn = document.getElementById('gridView');
    const listViewBtn = document.getElementById('listView');

    if (gridViewBtn && listViewBtn) {
        gridViewBtn.addEventListener('click', function() {
            setViewMode('grid');
        });

        listViewBtn.addEventListener('click', function() {
            setViewMode('list');
        });
    }
}

function setViewMode(mode) {
    const gridViewBtn = document.getElementById('gridView');
    const listViewBtn = document.getElementById('listView');
    const itemsGrid = document.getElementById('itemsGrid');

    if (mode === 'grid') {
        gridViewBtn.classList.add('active');
        listViewBtn.classList.remove('active');
        itemsGrid.className = 'row g-3';
        document.querySelectorAll('.item-card').forEach(card => {
            card.className = 'col-xl-3 col-lg-4 col-md-6 item-card';
        });
    } else {
        listViewBtn.classList.add('active');
        gridViewBtn.classList.remove('active');
        itemsGrid.className = 'row g-2';
        document.querySelectorAll('.item-card').forEach(card => {
            card.className = 'col-12 item-card';
            // Add list view specific styling
            const cardElement = card.querySelector('.card');
            if (cardElement) {
                cardElement.classList.add('d-md-flex', 'flex-md-row');
            }
        });
    }

    // Save preference
    localStorage.setItem('viewMode', mode);
}

// Loading state
function showLoadingState() {
    const itemsGrid = document.getElementById('itemsGrid');
    if (itemsGrid) {
        itemsGrid.innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Загрузка...</span>
                </div>
                <p class="mt-3 text-muted">Применяем фильтры...</p>
            </div>
        `;
    }
}

// Enhanced cart functionality
function updateCartCount() {
    let cart = JSON.parse(localStorage.getItem('cart') || '[]');
    let totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
    let cartBadge = document.querySelector('.cart-count');
    
    if (cartBadge) { 
        cartBadge.textContent = totalItems; 
        cartBadge.style.display = totalItems > 0 ? 'inline' : 'none'; 
    }
}

// Add to cart with animation
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('add-to-cart-btn') || e.target.closest('.add-to-cart-btn')) {
        e.preventDefault();
        const btn = e.target.closest('.add-to-cart-btn');
        const itemId = btn.dataset.itemId;
        const offerId = btn.dataset.offerId;
        const card = btn.closest('.card');
        const itemName = card.querySelector('h6').textContent;
        const itemPrice = card.querySelector('.fw-bold').textContent.replace(/[^\d.]/g, '');
        
        // Add loading state to button
        const originalContent = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        btn.disabled = true;
        
        setTimeout(() => {
            addToCart(offerId, itemName, itemPrice);
            btn.innerHTML = '<i class="fas fa-check"></i>';
            
            setTimeout(() => {
                btn.innerHTML = originalContent;
                btn.disabled = false;
            }, 1000);
        }, 300);
    }
});

function addToCart(offerId, itemName, itemPrice) {
    let cart = JSON.parse(localStorage.getItem('cart') || '[]');
    let existingItem = cart.find(item => item.offerId === offerId);
    
    if (existingItem) { 
        existingItem.quantity += 1; 
    } else { 
        cart.push({ 
            offerId: offerId, 
            name: itemName, 
            price: parseFloat(itemPrice), 
            quantity: 1 
        }); 
    }
    
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartCount();
    showNotification(`${itemName} добавлен в корзину!`, 'success');
}

// Favorite functionality with animation
document.addEventListener('click', function(e) {
    if (e.target.closest('.favorite-btn')) {
        e.preventDefault();
        const btn = e.target.closest('.favorite-btn');
        const itemId = btn.dataset.itemId;
        toggleFavorite(itemId, btn);
    }
});

function toggleFavorite(itemId, btn) {
    let favorites = JSON.parse(localStorage.getItem('favorites') || '[]');
    const isFavorite = favorites.includes(itemId);
    const icon = btn.querySelector('i');
    
    if (isFavorite) {
        favorites = favorites.filter(id => id !== itemId);
        icon.className = 'far fa-heart';
        btn.classList.remove('text-danger');
        showNotification('Удалено из избранного', 'info');
    } else {
        favorites.push(itemId);
        icon.className = 'fas fa-heart';
        btn.classList.add('text-danger');
        showNotification('Добавлено в избранное', 'success');
    }
    
    localStorage.setItem('favorites', JSON.stringify(favorites));
}

// Initialize favorites on page load
function initializeFavorites() {
    const favorites = JSON.parse(localStorage.getItem('favorites') || '[]');
    document.querySelectorAll('.favorite-btn').forEach(btn => {
        const itemId = btn.dataset.itemId;
        if (favorites.includes(itemId)) {
            btn.querySelector('i').className = 'fas fa-heart';
            btn.classList.add('text-danger');
        }
    });
}

// Distance calculation
function calculateDistances() {
    const distanceInfos = document.querySelectorAll('.distance-info');
    
    if (navigator.geolocation && distanceInfos.length > 0) {
        navigator.geolocation.getCurrentPosition(function(position) {
            const userLat = position.coords.latitude;
            const userLng = position.coords.longitude;
            
            distanceInfos.forEach(info => {
                const lat = parseFloat(info.dataset.lat);
                const lng = parseFloat(info.dataset.lng);
                
                if (lat && lng) {
                    const distance = calculateDistance(userLat, userLng, lat, lng);
                    info.textContent = `${distance} км`;
                }
            });
        }, function(error) {
            distanceInfos.forEach(info => {
                info.textContent = 'Недоступно';
            });
        });
    }
}

function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const lat1Rad = lat1 * Math.PI / 180;
    const lat2Rad = lat2 * Math.PI / 180;

    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1Rad) * Math.cos(lat2Rad);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;

    return distance.toFixed(1);
}

// Load more functionality
document.addEventListener('click', function(e) {
    if (e.target.id === 'loadMoreBtn') {
        e.preventDefault();
        loadMoreItems();
    }
});

function loadMoreItems() {
    const btn = document.getElementById('loadMoreBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Загрузка...';
    btn.disabled = true;
    
    const url = new URL(window.location);
    const currentPage = parseInt(url.searchParams.get('page') || '1');
    url.searchParams.set('page', currentPage + 1);
    
    fetch(url.toString())
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newItems = doc.querySelectorAll('.item-card');
            const itemsGrid = document.getElementById('itemsGrid');
            
            newItems.forEach(item => {
                itemsGrid.appendChild(item);
            });
            
            // Update results count
            const resultsCount = document.getElementById('results-count');
            if (resultsCount) {
                const currentCount = parseInt(resultsCount.textContent);
                resultsCount.textContent = currentCount + newItems.length;
            }
            
            // Hide load more button if no more items
            if (newItems.length < 12) {
                btn.style.display = 'none';
            } else {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
            
            // Reinitialize for new items
            calculateDistances();
            initializeFavorites();
        })
        .catch(error => {
            console.error('Error loading more items:', error);
            showNotification('Ошибка при загрузке товаров', 'error');
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
}

// Enhanced notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px; animation: slideInRight 0.3s ease;';
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }
    }, 3000);
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Global variables for user location
let userLocation = {
    lat: null,
    lng: null,
    isDetected: false
};

// Auto-detect user location on page load
function autoDetectLocation() {
    console.log('🔍 Starting auto location detection...');
    
    // Check if we're on HTTPS or localhost (required for geolocation)
    const isSecure = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
    console.log('🔒 Secure context:', isSecure);
    
    // Check if location is already stored in localStorage
    const storedLocation = localStorage.getItem('userLocation');
    if (storedLocation) {
        try {
            const location = JSON.parse(storedLocation);
            const now = Date.now();
            console.log('💾 Found stored location:', location);
            
            // Use stored location if it's less than 1 hour old
            if (location.timestamp && (now - location.timestamp) < 3600000) {
                userLocation = {
                    lat: location.lat,
                    lng: location.lng,
                    isDetected: true
                };
                console.log('✅ Using cached location:', userLocation);
                calculateDistancesWithStoredLocation();
                return;
            } else {
                console.log('⏰ Cached location expired, requesting fresh location');
            }
        } catch (e) {
            console.log('❌ Invalid stored location data:', e);
        }
    } else {
        console.log('📍 No cached location found');
    }
    
    // Check geolocation support
    if (!navigator.geolocation) {
        console.log('❌ Geolocation not supported by browser');
        const distanceInfos = document.querySelectorAll('.distance-info');
        distanceInfos.forEach(info => {
            info.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Геолокация недоступна';
            info.classList.add('text-muted');
        });
        return;
    }
    
    console.log('🌍 Geolocation supported, requesting position...');
    
    // Show loading indicator for distance elements
    const distanceInfos = document.querySelectorAll('.distance-info');
    console.log('📊 Found', distanceInfos.length, 'distance elements');
    
    distanceInfos.forEach(info => {
        info.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Определяем...';
        console.log('📍 Branch coordinates:', info.dataset.lat, info.dataset.lng);
    });
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            console.log('✅ Location detected successfully!');
            console.log('📍 User coordinates:', position.coords.latitude, position.coords.longitude);
            console.log('🎯 Accuracy:', position.coords.accuracy, 'meters');
            
            userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
                isDetected: true
            };
            
            // Store location with timestamp
            const locationData = {
                lat: userLocation.lat,
                lng: userLocation.lng,
                timestamp: Date.now()
            };
            localStorage.setItem('userLocation', JSON.stringify(locationData));
            console.log('💾 Location cached for future use');
            
            calculateDistancesWithStoredLocation();
            
            // Show success notification
            showNotification('Местоположение определено', 'success');
        },
        function(error) {
            console.error('❌ Geolocation error:', error);
            console.log('Error code:', error.code);
            console.log('Error message:', error.message);
            handleLocationError(error);
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 300000 // 5 minutes
        }
    );
}

function handleLocationError(error) {
    let errorMessage = 'Не удалось определить местоположение';
    let debugMessage = '';
    
    switch(error.code) {
        case error.PERMISSION_DENIED:
            errorMessage = 'Доступ к геолокации запрещен';
            debugMessage = 'User denied geolocation permission';
            break;
        case error.POSITION_UNAVAILABLE:
            errorMessage = 'Местоположение недоступно';
            debugMessage = 'Position unavailable (GPS/network issue)';
            break;
        case error.TIMEOUT:
            errorMessage = 'Время ожидания истекло';
            debugMessage = 'Geolocation request timed out';
            break;
        default:
            debugMessage = 'Unknown geolocation error';
    }
    
    console.log('🚨 Location error:', debugMessage);
    console.log('💡 Suggestion: Check browser permissions and HTTPS connection');
    
    const distanceInfos = document.querySelectorAll('.distance-info');
    distanceInfos.forEach(info => {
        info.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Недоступно';
        info.classList.add('text-muted');
    });
    
    showNotification(errorMessage, 'warning');
}

function calculateDistancesWithStoredLocation() {
    console.log('🧮 Starting distance calculations...');
    
    if (!userLocation.isDetected) {
        console.log('❌ User location not detected yet');
        return;
    }
    
    const distanceInfos = document.querySelectorAll('.distance-info');
    console.log('📊 Calculating distances for', distanceInfos.length, 'items');
    console.log('👤 User location:', userLocation.lat, userLocation.lng);
    
    let calculatedCount = 0;
    let errorCount = 0;
    
    distanceInfos.forEach((info, index) => {
        const lat = parseFloat(info.dataset.lat);
        const lng = parseFloat(info.dataset.lng);
        
        console.log(`🏪 Item ${index + 1}: Branch coordinates:`, lat, lng);
        
        if (lat && lng && !isNaN(lat) && !isNaN(lng)) {
            const distance = calculateDistance(userLocation.lat, userLocation.lng, lat, lng);
            info.innerHTML = `<i class="fas fa-location-dot me-1"></i>${distance} км`;
            info.classList.remove('text-muted');
            console.log(`✅ Item ${index + 1}: Distance calculated:`, distance);
            calculatedCount++;
        } else {
            console.log(`❌ Item ${index + 1}: Invalid coordinates:`, lat, lng);
            info.innerHTML = '<i class="fas fa-map-marker-alt me-1"></i>Адрес не указан';
            info.classList.add('text-muted');
            errorCount++;
        }
    });
    
    console.log(`📈 Distance calculation summary: ${calculatedCount} successful, ${errorCount} failed`);
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeFavorites();
    autoDetectLocation();
    
    // Restore view mode preference
    const savedViewMode = localStorage.getItem('viewMode');
    if (savedViewMode) {
        setViewMode(savedViewMode);
    }
    
    // Set quick filter based on URL params
    const urlParams = new URLSearchParams(window.location.search);
    const type = urlParams.get('type');
    const discount = urlParams.get('discount');
    
    if (type === 'dishes') {
        document.getElementById('filter-dishes').checked = true;
    } else if (type === 'products') {
        document.getElementById('filter-products').checked = true;
    } else if (discount) {
        document.getElementById('filter-discount').checked = true;
    }
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
