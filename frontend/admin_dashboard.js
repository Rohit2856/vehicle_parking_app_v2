const { createApp } = Vue;

createApp({
    data() {
        return {
            user: null,
            token: localStorage.getItem('token'),
            activeTab: 'overview',
            error: '',
            loginForm: {
                username: '',
                password: ''
            },
            dashboardSummary: null,
            parkingLots: [],
            parkingSpots: [],
            users: [],
            showCreateLotModal: false,
            showViewModal: false,
            showEditModal: false,
            selectedLotDetails: null,
            editLotData: {
                id: null,
                prime_location_name: '',
                price: '',
                address: '',
                pin_code: '',
                number_of_spots: ''
            },
            newLot: {
                prime_location_name: '',
                price: '',
                address: '',
                pin_code: '',
                number_of_spots: ''
            },
            analyticsData: null,
            revenueSummary: null,
            charts: {
                dailyReservations: null,
                lotOccupancy: null,
                monthlyRevenue: null,
                durationDistribution: null
            }
        }
    },
    mounted() {
        if (this.token) {
            this.verifyToken();
        }
    },
    methods: {
        async login() {
            try {
                const response = await axios.post('http://localhost:5000/auth/login', this.loginForm);
                this.token = response.data.access_token;
                this.user = response.data.user;
                localStorage.setItem('token', this.token);
                this.error = '';
                
                if (this.user.role === 'admin') {
                    this.fetchDashboardSummary();
                }
            } catch (error) {
                this.error = error.response?.data?.error || 'Login failed';
            }
        },
        
        async verifyToken() {
            try {
                const response = await axios.get('http://localhost:5000/auth/verify', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.user = response.data.user;
                
                if (this.user.role === 'admin') {
                    this.fetchDashboardSummary();
                }
            } catch (error) {
                this.logout();
            }
        },
        
        logout() {
            this.user = null;
            this.token = null;
            localStorage.removeItem('token');
        },
        
        async fetchDashboardSummary() {
            try {
                const response = await axios.get('http://localhost:5000/admin/dashboard/summary', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.dashboardSummary = response.data;
            } catch (error) {
                console.error('Failed to fetch dashboard summary:', error);
            }
        },
        
        async fetchParkingLots() {
            try {
                const response = await axios.get('http://localhost:5000/admin/lots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingLots = response.data.lots;
            } catch (error) {
                console.error('Failed to fetch parking lots:', error);
            }
        },
        
        async fetchParkingSpots() {
            try {
                const response = await axios.get('http://localhost:5000/admin/spots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingSpots = response.data.spots;
            } catch (error) {
                console.error('Failed to fetch parking spots:', error);
            }
        },
        
        async fetchUsers() {
            try {
                const response = await axios.get('http://localhost:5000/admin/users', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.users = response.data.users;
            } catch (error) {
                console.error('Failed to fetch users:', error);
            }
        },
        
        async createParkingLot() {
            try {
                const response = await axios.post('http://localhost:5000/admin/lots', this.newLot, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.showCreateLotModal = false;
                this.newLot = {
                    prime_location_name: '',
                    price: '',
                    address: '',
                    pin_code: '',
                    number_of_spots: ''
                };
                this.fetchParkingLots();
                alert('Parking lot created successfully!');
            } catch (error) {
                alert('Failed to create parking lot: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },
        
        async viewLotDetails(lotId) {
            try {
                const response = await axios.get(`http://localhost:5000/admin/lots/${lotId}`, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.selectedLotDetails = response.data.lot_details;
                this.showViewModal = true;
            } catch (error) {
                alert('Failed to fetch lot details: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },
        
        editLot(lot) {
            // Copy lot data to edit form
            this.editLotData = {
                id: lot.id,
                prime_location_name: lot.prime_location_name,
                price: lot.price,
                address: lot.address || '',
                pin_code: lot.pin_code || '',
                number_of_spots: lot.number_of_spots
            };
            this.showEditModal = true;
        },
        
        async updateParkingLot() {
            try {
                const response = await axios.put(`http://localhost:5000/admin/lots/${this.editLotData.id}`, 
                    this.editLotData, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.showEditModal = false;
                this.fetchParkingLots();
                alert('Parking lot updated successfully!');
            } catch (error) {
                alert('Failed to update parking lot: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },
        
        async deleteLot(lotId) {
            if (confirm('Are you sure you want to delete this parking lot?')) {
                try {
                    await axios.delete(`http://localhost:5000/admin/lots/${lotId}`, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    this.fetchParkingLots();
                    alert('Parking lot deleted successfully!');
                } catch (error) {
                    alert('Failed to delete parking lot: ' + (error.response?.data?.error || 'Unknown error'));
                }
            }
        },
        
        async fetchAnalytics() {
            try {
                // Fetch parking statistics
                const analyticsResponse = await axios.get('http://localhost:5000/analytics/admin/parking-stats', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                // Fetch revenue summary
                const revenueResponse = await axios.get('http://localhost:5000/analytics/admin/revenue-summary', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                // Ensure data exists before assignment
                this.analyticsData = analyticsResponse.data || {};
                this.revenueSummary = revenueResponse.data || {};
                
                // Debug: Log the data structure
                console.log('Analytics Data:', this.analyticsData);
                console.log('Revenue Data:', this.revenueSummary);
                
                // Wait for DOM update then create charts
                await this.$nextTick();
                
                // Add delay to ensure canvas elements are rendered
                setTimeout(() => {
                    this.createCharts();
                }, 300);
                
            } catch (error) {
                console.error('Failed to fetch analytics:', error);
                // Set default empty data structure
                this.analyticsData = {
                    daily_reservations: [],
                    lot_occupancy: [],
                    monthly_revenue: [],
                    duration_distribution: []
                };
                this.revenueSummary = {
                    total_revenue: 0,
                    today_revenue: 0,
                    month_revenue: 0,
                    average_revenue: 0
                };
            }
        },

        
        createCharts() {
            if (!this.analyticsData) return;
            
            // Daily Reservations Chart
            this.createDailyReservationsChart();
            
            // Lot Occupancy Chart
            this.createLotOccupancyChart();
            
            // Monthly Revenue Chart
            this.createMonthlyRevenueChart();
            
            // Duration Distribution Chart
            this.createDurationDistributionChart();
        },
        
        createDailyReservationsChart() {
            const ctx = document.getElementById('dailyReservationsChart');
            if (!ctx) {
                console.error('Canvas dailyReservationsChart not found');
                return;
            }
            
            const ctxContext = ctx.getContext('2d');
            
            if (this.charts.dailyReservations) {
                this.charts.dailyReservations.destroy();
            }
            
            // Safe data access with fallback
            const dailyReservations = this.analyticsData?.daily_reservations || [];
            
            this.charts.dailyReservations = new Chart(ctxContext, {
                type: 'line',
                data: {
                    labels: dailyReservations.map(d => d.date || 'Unknown'),
                    datasets: [{
                        label: 'Daily Reservations',
                        data: dailyReservations.map(d => d.reservations || 0),
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },

        createLotOccupancyChart() {
            const ctx = document.getElementById('lotOccupancyChart');
            if (!ctx) return;
            
            const ctxContext = ctx.getContext('2d');
            
            if (this.charts.lotOccupancy) {
                this.charts.lotOccupancy.destroy();
            }
            
            // Safe data access
            const lotOccupancy = this.analyticsData?.lot_occupancy || [];
            
            this.charts.lotOccupancy = new Chart(ctxContext, {
                type: 'bar',
                data: {
                    labels: lotOccupancy.map(l => l.lot_name || 'Unknown'),
                    datasets: [{
                        label: 'Occupancy Rate (%)',
                        data: lotOccupancy.map(l => l.occupancy_rate || 0),
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        },

        createMonthlyRevenueChart() {
            const ctx = document.getElementById('monthlyRevenueChart');
            if (!ctx) return;
            
            const ctxContext = ctx.getContext('2d');
            
            if (this.charts.monthlyRevenue) {
                this.charts.monthlyRevenue.destroy();
            }
            
            // Safe data access
            const monthlyRevenue = this.analyticsData?.monthly_revenue || [];
            
            this.charts.monthlyRevenue = new Chart(ctxContext, {
                type: 'bar',
                data: {
                    labels: monthlyRevenue.map(m => m.month || 'Unknown'),
                    datasets: [{
                        label: 'Monthly Revenue ($)',
                        data: monthlyRevenue.map(m => m.revenue || 0),
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        },

        createDurationDistributionChart() {
            const ctx = document.getElementById('durationDistributionChart');
            if (!ctx) return;
            
            const ctxContext = ctx.getContext('2d');
            
            if (this.charts.durationDistribution) {
                this.charts.durationDistribution.destroy();
            }
            
            // Safe data access
            const durationDistribution = this.analyticsData?.duration_distribution || [];
            
            this.charts.durationDistribution = new Chart(ctxContext, {
                type: 'doughnut',
                data: {
                    labels: durationDistribution.map(d => d.label || 'Unknown'),
                    datasets: [{
                        data: durationDistribution.map(d => d.count || 0),
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.5)',
                            'rgba(54, 162, 235, 0.5)',
                            'rgba(255, 205, 86, 0.5)',
                            'rgba(75, 192, 192, 0.5)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 205, 86, 1)',
                            'rgba(75, 192, 192, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        },

        
        formatDateTime(dateString) {
            if (!dateString) return '-';
            return new Date(dateString).toLocaleString();
        }
    }
}).mount('#app');
