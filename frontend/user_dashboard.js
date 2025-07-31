const { createApp } = Vue;

createApp({
    data() {
        return {
            user: null,
            token: localStorage.getItem('token'),
            activeTab: 'dashboard',
            error: '',
            showRegister: false,
            registerForm: {
                username: '',
                password: ''
            },
            dashboardData: null,
            availableLots: [],
            parkingHistory: [],
            currentReservation: null,
            userAnalytics: null,
            userChartInstances: {},
            isLoading: false,
            showProfileModal: false,
            profileData: {},
            profileStats: {},
            errors: {},
            
            // Loading States
            isLoadingDashboard: false,
            isLoadingLots: false,
            isLoadingHistory: false,
            isReserving: false,
            isReleasing: false,
            
            showBookingModal: false,
            bookingDetails: {},
            
            toastMessage: '',
            toastType: 'success'
        }
    },
    mounted() {
        if (this.token) {
            this.verifyToken();
        }
    },
    methods: {
        showToast(message, type = 'success') {
            this.toastMessage = message;
            this.toastType = type;
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} position-fixed toast-notification`;
            toast.style.cssText = `
                top: 20px; 
                right: 20px; 
                z-index: 9999; 
                min-width: 300px;
                animation: slideInRight 0.3s ease;
                box-shadow: 0 8px 16px rgba(0,0,0,0.15);
            `;
            toast.innerHTML = `
                <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'} me-2"></i>
                <strong>${message}</strong>
            `;
            
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        },

        async register() {
            try {
                const response = await axios.post('/auth/register', this.registerForm);
                this.showRegister = false;
                this.registerForm = { username: '', password: '' };
                this.showToast('Registration successful! Please login.', 'success');
            } catch (error) {
                this.showToast('Registration failed: ' + (error.response?.data?.error || 'Unknown error'), 'error');
            }
        },

        async verifyToken() {
            try {
                const response = await axios.get('/auth/verify', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.user = response.data.user;
                if (this.user.role === 'user') {
                    this.fetchDashboard();
                    this.fetchCurrentReservation();
                }
            } catch (error) {
                this.logout();
            }
        },

        logout() {
            this.user = null;
            this.token = null;
            localStorage.removeItem('token');
            window.location.href = 'index.html'
        },

        async openMyProfile() {
            try {
                const response = await axios.get('/profile/me', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.profileData = {
                    username: response.data.profile.username || this.user.username,
                    email: response.data.profile.email || '',
                    full_name: response.data.profile.full_name || '',
                    mobile_number: response.data.profile.mobile_number || '',
                    vehicle_type: response.data.profile.vehicle_type || '',
                    vehicle_number: response.data.profile.vehicle_number || '',
                    vehicle_brand: response.data.profile.vehicle_brand || '',
                    home_address: response.data.profile.home_address || ''
                };
                
                this.profileStats = response.data.stats || {
                    total_reservations: 0,
                    total_spent: 0,
                    member_since: 'Recently joined'
                };
                
                this.showProfileModal = true;
                this.errors = {};
            } catch (error) {
                this.showToast('Failed to load profile: ' + (error.response?.data?.error || 'Network error'), 'error');
            }
        },

        async saveUserProfile() {
            try {
                const updateData = {
                    email: this.profileData.email,
                    mobile_number: this.profileData.mobile_number,
                    full_name: this.profileData.full_name,
                    vehicle_type: this.profileData.vehicle_type,
                    vehicle_number: this.profileData.vehicle_number,
                    vehicle_brand: this.profileData.vehicle_brand,
                    home_address: this.profileData.home_address
                };

                const response = await axios.put('/profile/me', updateData, {
                    headers: { 
                        Authorization: `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.status === 200) {
                    this.showToast('Profile updated successfully!', 'success');
                    this.showProfileModal = false;
                    this.errors = {};
                }
            } catch (error) {
                this.errors = error.response?.data?.errors || {};
                this.showToast('Failed to update profile: ' + (error.response?.data?.error || 'Unknown error'), 'error');
            }
        },

        async fetchDashboard() {
            try {
                this.isLoadingDashboard = true;
                const response = await axios.get('/user/dashboard', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.dashboardData = response.data;
            } catch (error) {
                this.dashboardData = {
                    total_bookings: 0,
                    total_spent: 0,
                    avg_duration: 0,
                    favorite_location: 'None'
                };
                this.showToast('Failed to load dashboard data', 'error');
            } finally {
                this.isLoadingDashboard = false;
            }
        },

        async fetchAvailableLots() {
            try {
                this.isLoadingLots = true;
                const response = await axios.get('/user/lots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.availableLots = response.data.available_lots;
            } catch (error) {
                this.availableLots = [];
                this.showToast('Failed to load parking lots', 'error');
            } finally {
                this.isLoadingLots = false;
            }
        },

        async fetchHistory() {
            try {
                this.isLoadingHistory = true;
                const response = await axios.get('/user/history', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingHistory = response.data.history;
            } catch (error) {
                this.parkingHistory = [];
                this.showToast('Failed to load parking history', 'error');
            } finally {
                this.isLoadingHistory = false;
            }
        },

        async fetchCurrentReservation() {
            try {
                const response = await axios.get('/user/current-reservation', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.currentReservation = response.data.active_reservation;
                console.log('Current reservation:', this.currentReservation); // Debug log
            } catch (error) {
                this.currentReservation = null;
            }
        },

        canReserveSpot(lotId) {
            if (!this.currentReservation) {
                return true; 
            }
            return this.currentReservation.lot_id === lotId;
        },

        getReserveButtonText(lot) {
            if (this.isReserving) return 'Reserving...';
            
            if (this.currentReservation) {
                if (this.currentReservation.lot_id === lot.id) {
                    return 'Release';
                } else {
                    return 'Reserve';
                }
            }
            
            return 'Reserve';
        },

        getReserveButtonClass(lot) {
            if (this.isReserving) return 'btn btn-gradient-warning';
            
            if (this.currentReservation) {
                if (this.currentReservation.lot_id === lot.id) {
                    return 'btn btn-gradient-danger'; 
                } else {
                    return 'btn btn-secondary';
                }
            }
            return 'btn btn-gradient-primary';
        },

        async handleLotButtonClick(lot) {
            if (this.currentReservation) {
                if (this.currentReservation.lot_id === lot.id) {
                    await this.releaseSpot(this.currentReservation.reservation_id);
                } else {
                    this.showToast('You must release your current parking spot first', 'warning');
                }
            } else {
                await this.reserveSpot(lot.id);
            }
        },

        isLotButtonDisabled(lot) {
            if (this.isReserving || this.isReleasing) return true;
            
            if (this.currentReservation) {
                return this.currentReservation.lot_id !== lot.id;
            }
            return false;
        },

        async reserveSpot(lotId) {
            if (this.currentReservation) {
                this.showToast('You already have an active reservation', 'warning');
                return;
            }

            try {
                this.isReserving = true;
                const response = await axios.post('/user/reserve', {
                    lot_id: lotId
                }, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });

                this.bookingDetails = {
                    lot_id: response.data.reservation.lot_id,
                    spot_id: response.data.reservation.spot_id,
                    user_id: this.user.id,
                    vehicle_number: this.user.vehicle_number || 'Not specified',
                    parking_timestamp: response.data.reservation.parking_timestamp,
                    hourly_rate: response.data.reservation.hourly_rate,
                    lot_name: response.data.reservation.lot_name
                };
                
                this.showBookingModal = true;

                await this.fetchCurrentReservation();
                await this.fetchAvailableLots();
                await this.fetchDashboard();
                
            } catch (error) {
                this.showToast('Reservation failed: ' + (error.response?.data?.error || 'Unknown error'), 'error');
            } finally {
                this.isReserving = false;
            }
        },

        closeBookingModal() {
            this.showBookingModal = false;
            this.bookingDetails = {};
        },

        async releaseSpot(reservationId) {
            if (confirm('Are you sure you want to release this parking spot?')) {
                try {
                    this.isReleasing = true;
                    const response = await axios.post(`/user/release/${reservationId}`, {}, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    
                    this.showToast(`Spot released successfully! Cost: ₹${response.data.parking_cost}`, 'success');
                    this.currentReservation = null;
                    await this.fetchDashboard();
                    await this.fetchHistory();
                } catch (error) {
                    this.showToast('Release failed: ' + (error.response?.data?.error || 'Unknown error'), 'error');
                } finally {
                    this.isReleasing = false;
                }
            }
        },

        async fetchUserAnalytics() {
            try {
                this.isLoading = true;
                const response = await axios.get('/analytics/user/parking-stats', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.userAnalytics = response.data;
                await this.$nextTick();
                setTimeout(() => this.createUserCharts(), 100);
                
            } catch (error) {
                this.userAnalytics = {
                    spending_trend: [
                        { month: 'Jan', amount: 5 }, { month: 'Feb', amount: 10 },
                        { month: 'Mar', amount: 15 }, { month: 'Apr', amount: 8 },
                        { month: 'May', amount: 20 }, { month: 'Jun', amount: 25 }
                    ],
                    favorite_locations: [{ name: 'Sample Location', visits: 3 }],
                    duration_preferences: [
                        { label: '< 1 hour', count: 2 }, { label: '1-3 hours', count: 5 },
                        { label: '3-6 hours', count: 3 }, { label: '6+ hours', count: 1 }
                    ],
                    weekly_activity: [
                        { day: 'Mon', bookings: 2 }, { day: 'Tue', bookings: 1 },
                        { day: 'Wed', bookings: 3 }, { day: 'Thu', bookings: 2 },
                        { day: 'Fri', bookings: 4 }, { day: 'Sat', bookings: 1 }, { day: 'Sun', bookings: 0 }
                    ]
                };
                await this.$nextTick();
                setTimeout(() => this.createUserCharts(), 100);
            } finally {
                this.isLoading = false;
            }
        },

        createUserCharts() {
            this.destroyUserCharts();
            if (!this.userAnalytics) return;

            // Spending chart
            const spendingCanvas = document.getElementById('userSpendingChart');
            if (spendingCanvas) {
                const maxSpending = Math.max(...this.userAnalytics.spending_trend.map(s => s.amount));
                const avgSpending = this.userAnalytics.spending_trend.reduce((sum, s) => sum + s.amount, 0) / this.userAnalytics.spending_trend.length;
                
                this.userChartInstances.spending = new Chart(spendingCanvas, {
                    type: 'line',
                    data: {
                        labels: this.userAnalytics.spending_trend.map(s => s.month),
                        datasets: [{
                            label: 'Monthly Spending (₹)',
                            data: this.userAnalytics.spending_trend.map(s => s.amount),
                            borderColor: '#1e3a8a',
                            backgroundColor: (ctx) => {
                                const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, 400);
                                gradient.addColorStop(0, 'rgba(30, 58, 138, 0.3)');
                                gradient.addColorStop(1, 'rgba(30, 58, 138, 0.05)');
                                return gradient;
                            },
                            borderWidth: 3,
                            tension: 0.4,
                            fill: true,
                            pointRadius: 8,
                            pointHoverRadius: 12,
                            pointBackgroundColor: '#fff',
                            pointBorderWidth: 3,
                            pointBorderColor: '#1e3a8a'
                        }, {
                            label: 'Average',
                            data: Array(this.userAnalytics.spending_trend.length).fill(avgSpending),
                            borderColor: '#f97316',
                            borderDash: [5, 5],
                            borderWidth: 2,
                            fill: false,
                            pointRadius: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top',
                                labels: {
                                    color: '#1f2937',
                                    font: { size: 12, weight: 'bold' },
                                    usePointStyle: true
                                }
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                backgroundColor: 'rgba(0,0,0,0.8)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                callbacks: {
                                    afterBody: function(context) {
                                        const current = context[0].parsed.y;
                                        const trend = current > avgSpending ? '📈 Above average' : '📉 Below average';
                                        return [`${trend}`, `Avg: ₹${avgSpending.toFixed(0)}`];
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: { color: 'rgba(107, 114, 128, 0.2)' },
                                ticks: {
                                    callback: (value) => `₹${value}`,
                                    color: '#1f2937',
                                    font: { size: 11, weight: '600' }
                                }
                            },
                            x: {
                                grid: { display: false },
                                ticks: {
                                    color: '#1f2937',
                                    font: { size: 11, weight: '600' }
                                }
                            }
                        }
                    }
                });
            }

            // Favorite Locations chart  
            const locationsCanvas = document.getElementById('userLocationsChart');
            if (locationsCanvas) {
                const totalVisits = this.userAnalytics.favorite_locations.reduce((sum, l) => sum + l.visits, 0);
                
                this.userChartInstances.locations = new Chart(locationsCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: this.userAnalytics.favorite_locations.map(l => l.name),
                        datasets: [{
                            data: this.userAnalytics.favorite_locations.map(l => l.visits),
                            backgroundColor: [
                                'rgba(30, 58, 138, 0.8)',   // Navy Blue
                                'rgba(249, 115, 22, 0.8)',  // Orange
                                'rgba(5, 150, 105, 0.8)',   // Green
                                'rgba(217, 119, 6, 0.8)',   // Yellow
                                'rgba(220, 38, 38, 0.8)'    // Red
                            ],
                            borderColor: '#fff',
                            borderWidth: 3,
                            hoverOffset: 15,
                            cutout: '60%' // Creates donut effect
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right',
                                labels: {
                                    color: '#1f2937',
                                    font: { size: 11, weight: 'bold' },
                                    usePointStyle: true,
                                    generateLabels: function(chart) {
                                        const data = chart.data;
                                        return data.labels.map((label, i) => {
                                            const visits = data.datasets[0].data[i];
                                            const percentage = ((visits / totalVisits) * 100).toFixed(1);
                                            return {
                                                text: `${label} (${percentage}%)`,
                                                fillStyle: data.datasets[0].backgroundColor[i],
                                                strokeStyle: data.datasets[0].borderColor,
                                                lineWidth: data.datasets[0].borderWidth,
                                                pointStyle: 'circle'
                                            };
                                        });
                                    }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const percentage = ((context.parsed / totalVisits) * 100).toFixed(1);
                                        return `${context.label}: ${context.parsed} visits (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    },
                    plugins: [{
                        id: 'centerText',
                        beforeDraw: function(chart) {
                            const ctx = chart.ctx;
                            ctx.save();
                            const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
                            const centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;
                            
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';
                            ctx.fillStyle = '#1f2937';
                            ctx.font = 'bold 16px Arial';
                            ctx.fillText(`${totalVisits}`, centerX, centerY - 10);
                            ctx.font = '12px Arial';
                            ctx.fillText('Total Visits', centerX, centerY + 10);
                            ctx.restore();
                        }
                    }]
                });
            }

            // STACKED BAR CHART Duration with Comparison
            const durationCanvas = document.getElementById('userDurationChart');
            if (durationCanvas) {
                this.userChartInstances.duration = new Chart(durationCanvas, {
                    type: 'bar',
                    data: {
                        labels: this.userAnalytics.duration_preferences.map(d => d.label),
                        datasets: [{
                            label: 'Your Usage',
                            data: this.userAnalytics.duration_preferences.map(d => d.count),
                            backgroundColor: 'rgba(30, 58, 138, 0.8)',
                            borderColor: '#1e3a8a',
                            borderWidth: 2,
                            borderRadius: 8,
                            borderSkipped: false
                        }, {
                            label: 'Typical Usage',
                            data: [3, 8, 4, 2], 
                            backgroundColor: 'rgba(249, 115, 22, 0.6)',
                            borderColor: '#f97316',
                            borderWidth: 2,
                            borderRadius: 8,
                            borderSkipped: false
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top',
                                labels: {
                                    color: '#1f2937',
                                    font: { size: 12, weight: 'bold' },
                                    usePointStyle: true
                                }
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                callbacks: {
                                    afterBody: function(context) {
                                        const userValue = context[0].parsed.y;
                                        const typicalValue = context[1] ? context[1].parsed.y : 0;
                                        if (userValue > typicalValue) {
                                            return '📊 You use this duration more than typical users';
                                        } else if (userValue < typicalValue) {
                                            return '⏱️ You use this duration less than typical users';
                                        }
                                        return '📈 Similar to typical usage pattern';
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: { color: 'rgba(107, 114, 128, 0.2)' },
                                ticks: {
                                    color: '#1f2937',
                                    font: { size: 11, weight: '600' }
                                }
                            },
                            x: {
                                grid: { display: false },
                                ticks: {
                                    color: '#1f2937',
                                    font: { size: 11, weight: '600' }
                                }
                            }
                        }
                    }
                });
            }

            // POLAR AREA CHART Weekly Activity with Insights
            const weeklyCanvas = document.getElementById('userWeeklyChart');
            if (weeklyCanvas) {
                const totalBookings = this.userAnalytics.weekly_activity.reduce((sum, w) => sum + w.bookings, 0);
                const avgBookings = totalBookings / 7;
                
                this.userChartInstances.weekly = new Chart(weeklyCanvas, {
                    type: 'polarArea',
                    data: {
                        labels: this.userAnalytics.weekly_activity.map(w => w.day),
                        datasets: [{
                            label: 'Bookings per Day',
                            data: this.userAnalytics.weekly_activity.map(w => w.bookings),
                            backgroundColor: [
                                'rgba(30, 58, 138, 0.7)',   // Monday
                                'rgba(249, 115, 22, 0.7)',  // Tuesday
                                'rgba(5, 150, 105, 0.7)',   // Wednesday
                                'rgba(217, 119, 6, 0.7)',   // Thursday
                                'rgba(220, 38, 38, 0.7)',   // Friday
                                'rgba(139, 69, 19, 0.7)',   // Saturday
                                'rgba(75, 0, 130, 0.7)'     // Sunday
                            ],
                            borderColor: '#fff',
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    color: '#1f2937',
                                    font: { size: 11, weight: 'bold' },
                                    usePointStyle: true,
                                    generateLabels: function(chart) {
                                        const data = chart.data;
                                        return data.labels.map((label, i) => {
                                            const bookings = data.datasets[0].data[i];
                                            const isAboveAvg = bookings > avgBookings;
                                            return {
                                                text: `${label} (${bookings}) ${isAboveAvg ? '📈' : '📉'}`,
                                                fillStyle: data.datasets[0].backgroundColor[i],
                                                strokeStyle: data.datasets[0].borderColor,
                                                lineWidth: data.datasets[0].borderWidth,
                                                pointStyle: 'circle'
                                            };
                                        });
                                    }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const value = context.parsed.r;
                                        const isAboveAvg = value > avgBookings;
                                        const insight = isAboveAvg ? 
                                            'High activity day for you' : 
                                            'Low activity day for you';
                                        return [`${context.label}: ${value} bookings`, insight];
                                    }
                                }
                            }
                        },
                        scales: {
                            r: {
                                beginAtZero: true,
                                grid: { color: 'rgba(107, 114, 128, 0.3)' },
                                pointLabels: {
                                    font: { size: 12, weight: 'bold' },
                                    color: '#1f2937'
                                },
                                ticks: {
                                    color: '#1f2937',
                                    font: { size: 10 },
                                    backdropColor: 'rgba(255, 255, 255, 0.8)'
                                }
                            }
                        }
                    }
                });
            }
        },

        destroyUserCharts() {
            Object.values(this.userChartInstances).forEach(chart => {
                if (chart) chart.destroy();
            });
            this.userChartInstances = {};
        },

        async exportMyData() {
            try {
                const response = await axios.post('/jobs/instant-csv-export', {
                    user_id: this.user.id
                }, {
                    headers: {
                        Authorization: `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    },
                    responseType: 'blob'
                });

                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.download = `my_parking_history_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);

                this.showToast('CSV file downloaded successfully!', 'success');
            } catch (error) {
                this.showToast('Download failed: ' + (error.response?.data?.error || 'Unable to download file'), 'error');
            }
        },

        formatDateTime(dateString) {
            if (!dateString) return '-';
            return new Date(dateString).toLocaleString('en-IN');
        }
    }
}).mount('#app');
