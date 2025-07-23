const { createApp } = Vue;

createApp({
    data() {
        return {
            user: null,
            token: localStorage.getItem('token'),
            activeTab: 'overview',
            error: '',
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
            },
            exportJobId: null,
            exportStatus: '',
            isLoading: false,
            searchQuery: '',
            spotStatusFilter: '',
            searchTimeout: null
        }
    },
    mounted() {
        if (this.token) {
            this.verifyToken();
        }
    },
    methods: {
        async verifyToken() {
            try {
                const response = await axios.get('/auth/verify', {
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
            window.location.href = 'index.html'
        },
        
        async fetchDashboardSummary() {
            try {
                const response = await axios.get('/admin/dashboard/summary', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.dashboardSummary = response.data;
            } catch (error) {
                console.error('Failed to fetch dashboard summary:', error);
            }
        },
        
        async fetchParkingLots() {
            try {
                const response = await axios.get('/admin/lots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingLots = response.data.lots;
            } catch (error) {
                console.error('Failed to fetch parking lots:', error);
            }
        },
        
        async fetchParkingSpots() {
            try {
                const response = await axios.get('/admin/spots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingSpots = response.data.spots;
            } catch (error) {
                console.error('Failed to fetch parking spots:', error);
            }
        },
        
        async fetchUsers() {
            try {
                const response = await axios.get('/admin/users', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.users = response.data.users;
            } catch (error) {
                console.error('Failed to fetch users:', error);
            }
        },
        
        async createParkingLot() {
            try {
                const response = await axios.post('/admin/lots', this.newLot, {
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
                const response = await axios.get(`/admin/lots/${lotId}`, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.selectedLotDetails = response.data.lot_details;
                this.showViewModal = true;
            } catch (error) {
                alert('Failed to fetch lot details: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },
        
        editLot(lot) {
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
                const response = await axios.put(`/admin/lots/${this.editLotData.id}`, 
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
                    await axios.delete(`/admin/lots/${lotId}`, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    this.fetchParkingLots();
                    alert('Parking lot deleted successfully!');
                } catch (error) {
                    alert('Failed to delete parking lot: ' + (error.response?.data?.error || 'Unknown error'));
                }
            }
        },
        async deleteIndividualSpot(spotId, spotInfo) {
            const confirmMessage = `Delete Spot ${spotId} from ${spotInfo.lot_name}?\n\nThis cannot be undone.`;
            
            if (confirm(confirmMessage)) {
                try {
                    await axios.delete(`/admin/spots/${spotId}/remove`, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    
                    await this.fetchParkingSpots(); // Refresh the list
                    alert(`Spot ${spotId} deleted successfully!`);
                    
                } catch (error) {
                    const errorMsg = error.response?.data?.error || 'Failed to delete spot';
                    alert(`Cannot delete spot: ${errorMsg}`);
                }
            }
        },
        getVehicleDisplay(spot) {
            return spot.vehicle_number && spot.vehicle_number !== '-' ? spot.vehicle_number : '-';
        },        
        async fetchAnalytics() {
            try {
                // Fetch parking statistics
                const analyticsResponse = await axios.get('/analytics/admin/parking-stats', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                // Fetch revenue summary
                const revenueResponse = await axios.get('/analytics/admin/revenue-summary', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                // To ensure data exists before assignment
                this.analyticsData = analyticsResponse.data || {};
                this.revenueSummary = revenueResponse.data || {};
                
                // Debug: Log the data structure
                console.log('Analytics Data:', this.analyticsData);
                console.log('Revenue Data:', this.revenueSummary);
                
                // Waiting for DOM update then create charts
                await this.$nextTick();
                
                // Adding delay to ensure canvas elements are rendered
                setTimeout(() => {
                    this.createCharts();
                }, 300);
                
            } catch (error) {
                console.error('Failed to fetch analytics:', error);
                // Set to default empty data structure
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

        async triggerCSVExport(exportType = 'admin') {
            try {
                const response = await axios.post('/jobs/trigger-csv-export', {
                    user_id: this.user.id,
                    export_type: exportType
                }, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.exportJobId = response.data.job_id;
                this.exportStatus = 'processing';
                
                // Checking job status periodically
                this.checkExportStatus();
                
            } catch (error) {
                alert('Failed to start CSV export: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },

        async checkExportStatus() {
            if (!this.exportJobId) return;
            
            try {
                const response = await axios.get(`/jobs/status/${this.exportJobId}`, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.exportStatus = response.data.state;
                
                if (response.data.state === 'SUCCESS') {
                    // Download ready
                    this.downloadCSV();
                } else if (response.data.state === 'FAILURE') {
                    alert('Export failed: ' + response.data.error);
                } else {
                    setTimeout(() => this.checkExportStatus(), 2000);
                }
                
            } catch (error) {
                console.error('Failed to check export status:', error);
            }
        },

        async downloadCSV() {
            try {
                const url = `/export/csv/download/${this.exportJobId}?user_id=${this.user.id}&export_type=admin`;
                const link = document.createElement('a');
                link.href = url;
                link.download = 'admin_parking_export.csv';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                this.exportJobId = null;
                this.exportStatus = '';
                
            } catch (error) {
                alert('Failed to download CSV');
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
                        label: 'Monthly Revenue (₹)',
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
        getSearchPlaceholder() {
            switch(this.activeTab) {
                case 'lots': return 'Search by location name, address, or pincode...';
                case 'spots': return 'Search by spot ID or lot name...';
                case 'users': return 'Search by username or email...';
                default: return 'Search...';
            }
        },

        performSearch() {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.executeSearch();
            }, 300);
        },

        async executeSearch() {
            try {
                const queryString = this.buildSearchQuery();
                let url = '';
                switch(this.activeTab) {
                    case 'lots':
                        url = '/admin/lots';
                        break;
                    case 'spots':
                        url = '/admin/spots';
                        break;
                    case 'users':
                        url = '/admin/users';
                        break;
                }
                
                if (queryString) url += `?${queryString}`;
                const response = await axios.get(url, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                switch(this.activeTab) {
                    case 'lots':
                        this.parkingLots = response.data.lots;
                        break;
                    case 'spots':
                        this.parkingSpots = response.data.spots;
                        break;
                    case 'users':
                        this.users = response.data.users;
                        break;
                }
            } catch (error) {
                console.error('Search failed:', error);
                this.error = 'Search failed. Please try again.';
            }
        },

        clearSearch() {
            this.searchQuery = '';
            this.spotStatusFilter = '';
            switch(this.activeTab) {
                case 'lots':
                    this.fetchParkingLots();
                    break;
                case 'spots':
                    this.fetchParkingSpots();
                    break;
                case 'users':
                    this.fetchUsers();
                    break;
            }
        },
        buildSearchQuery() {
            const params = new URLSearchParams();
            if (this.searchQuery.trim()) {
                params.append('q', this.searchQuery.trim());
            }
            if (this.activeTab === 'spots' && this.spotStatusFilter) {
                params.append('status', this.spotStatusFilter);
            }
            return params.toString();
        },

        getSearchResultsText() {
            let count = 0;
            let type = '';
            switch(this.activeTab) {
                case 'lots':
                    count = this.parkingLots.length;
                    type = 'parking lot(s)';
                    break;
                case 'spots':
                    count = this.parkingSpots.length;
                    type = 'parking spot(s)';
                    break;
                case 'users':
                    count = this.users.length;
                    type = 'user(s)';
                    break;
            }
            return `Found ${count} ${type}`;
        },
        
        formatDateTime(dateString) {
            if (!dateString) return '-';
            return new Date(dateString).toLocaleString();
        },
    }
}).mount('#app');
