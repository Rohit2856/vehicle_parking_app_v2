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
            summaryCards: [],
            lastUpdated: '',
            chartInstances: {},
            exportJobId: null,
            exportStatus: '',
            isLoading: false,
            searchQuery: '',
            spotStatusFilter: '',
            searchTimeout: null,

            showProfileModal: false,
            profileData: {},
            profileStats: {},
            usersList: [],
            selectedUser: null,
            userToDelete: null,
            deleteConfirmation: '',
            showUserDetailsModal: false,
            showDeleteModal: false,
            errors: {},

            recentActivities: [],
            systemStats: {},
            quickActions: []
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
                    this.activeTab = 'overview';
                    await this.fetchDashboardSummary();
                    await this.fetchOverviewData();
                }
            } catch (error) {
                this.logout();
            }
        },

        logout() {
            this.user = null;
            this.token = null;
            localStorage.removeItem('token');
            window.location.href = 'index.html';
        },

        async fetchDashboardSummary() {
            try {
                const [lotsRes, spotsRes, usersRes] = await Promise.all([
                    axios.get('/admin/lots', { headers: { Authorization: `Bearer ${this.token}` } }),
                    axios.get('/admin/spots', { headers: { Authorization: `Bearer ${this.token}` } }),
                    axios.get('/admin/users', { headers: { Authorization: `Bearer ${this.token}` } })
                ]);

                const lots = lotsRes.data.lots || [];
                const spots = spotsRes.data.spots || [];
                const users = usersRes.data.users || [];

                const totalRevenue = users.reduce((sum, user) => {
                    return sum + (user.parking_stats?.total_amount_spent || 0);
                }, 0);

                this.dashboardSummary = {
                    total_lots: lots.length,
                    total_spots: spots.length,
                    total_users: users.length,
                    occupied_spots: spots.filter(spot => spot.status === 'O' || spot.status === 'occupied').length,
                    available_spots: spots.filter(spot => spot.status === 'A' || spot.status === 'available').length,
                    active_reservations: users.filter(user => user.is_currently_parked).length,
                    total_revenue: totalRevenue
                };
                console.log('Dashboard Summary calculated:', this.dashboardSummary);
            } catch (error) {
                console.error('Failed to fetch dashboard summary:', error);
                this.dashboardSummary = {
                    total_lots: 0,
                    total_spots: 0,
                    total_users: 0,
                    occupied_spots: 0,
                    available_spots: 0,
                    active_reservations: 0,
                    total_revenue: 0
                };
            }
        },

        async fetchOverviewData() {
            try {
                await this.fetchRecentActivities();
                this.systemStats = {
                    occupancy_rate: this.dashboardSummary.total_spots > 0 ? 
                        Math.round((this.dashboardSummary.occupied_spots / this.dashboardSummary.total_spots) * 100) : 0,
                    avg_revenue_per_user: this.dashboardSummary.total_users > 0 ? 
                        Math.round(this.dashboardSummary.total_revenue / this.dashboardSummary.total_users) : 0,
                    system_uptime: '99.9%',
                    last_backup: 'Today, 3:00 AM'
                };

                this.quickActions = [
                    { title: 'Create New Lot', icon: 'fas fa-plus', action: () => this.showCreateLotModal = true, color: 'primary' },
                    { title: 'View Analytics', icon: 'fas fa-chart-line', action: () => { this.activeTab = 'analytics'; this.fetchAnalytics(); }, color: 'info' },
                    { title: 'Manage Users', icon: 'fas fa-users-cog', action: () => { this.activeTab = 'users'; this.loadUsersForManagement(); }, color: 'warning' },
                    { title: 'Export Data', icon: 'fas fa-download', action: () => this.triggerCSVExport('admin'), color: 'success' }
                ];
            } catch (error) {
                console.error('Failed to fetch overview data:', error);
            }
        },
        startActivityRefresh() {
            this.activityRefreshInterval = setInterval(() => {
                if (this.activeTab === 'overview') {
                    this.fetchRecentActivities();
                }
            }, 30000); // 30 seconds
        },

        stopActivityRefresh() {
            if (this.activityRefreshInterval) {
                clearInterval(this.activityRefreshInterval);
                this.activityRefreshInterval = null;
            }
        },

        async fetchRecentActivities() {
            try {
                const response = await axios.get('/admin/recent-activities', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.recentActivities = response.data.activities || [];
                if (this.recentActivities.length === 0) {
                    this.recentActivities = [
                        { 
                            type: 'info', 
                            message: 'No recent activities to display', 
                            time: 'System message', 
                            icon: 'fas fa-info-circle', 
                            color: 'secondary' 
                        }
                    ];
                }
            } catch (error) {
                console.error('Failed to fetch recent activities:', error);
                this.recentActivities = [
                    { type: 'user_registered', message: 'New user registered', time: '2 hours ago', icon: 'fas fa-user-plus', color: 'success' },
                    { type: 'lot_created', message: 'New parking lot created', time: '5 hours ago', icon: 'fas fa-plus-circle', color: 'info' },
                    { type: 'spot_occupied', message: 'Parking spot occupied', time: '1 hour ago', icon: 'fas fa-car', color: 'warning' }
                ];
            }
        },

        async refreshDashboard() {
            try {
                this.isLoading = true;
                await this.fetchDashboardSummary();
                await this.fetchOverviewData();
                this.lastUpdated = new Date().toLocaleTimeString('en-IN');
                
                alert('Dashboard refreshed successfully!');
            } catch (error) {
                console.error('Dashboard refresh failed:', error);
                alert('Failed to refresh dashboard');
            } finally {
                this.isLoading = false;
            }
        },

        async openMyProfile() {
            try {
                const response = await axios.get('/profile/me', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.profileData = {
                    username: response.data.profile.username || this.user.username,
                    email: response.data.profile.email || 'admin@vehicleparkingapp.com',
                    full_name: response.data.profile.full_name || 'System Administrator',
                    mobile_number: response.data.profile.mobile_number || '9999999999',
                    vehicle_type: response.data.profile.vehicle_type || 'Admin',
                    vehicle_number: response.data.profile.vehicle_number || 'ADMIN001',
                    vehicle_brand: response.data.profile.vehicle_brand || 'System Vehicle',
                    home_address: response.data.profile.home_address || 'System Address',
                    current_password: '' 
                };
                this.showProfileModal = true;
                this.errors = {};
            } catch (error) {
                console.error('Profile fetch error:', error);
                alert('Failed to load profile: ' + (error.response?.data?.error || 'Network error'));
            }
        },

        async saveAdminProfile() {
            if (!this.profileData.current_password) {
                alert('Please enter your admin password to confirm changes');
                return;
            }
            try {
                const updateData = {
                    email: this.profileData.email,
                    mobile_number: this.profileData.mobile_number,
                    full_name: this.profileData.full_name,
                    vehicle_type: this.profileData.vehicle_type,
                    vehicle_number: this.profileData.vehicle_number,
                    vehicle_brand: this.profileData.vehicle_brand,
                    home_address: this.profileData.home_address,
                    current_password: this.profileData.current_password
                };
                await axios.put('/profile/me', updateData, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                alert('Profile updated successfully!');
                this.showProfileModal = false;
                this.profileData.current_password = '';
                this.errors = {};
            } catch (error) {
                console.error('Profile update error:', error);
                this.errors = error.response?.data?.errors || {};
                alert('Failed to update profile: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },

        async loadUsersForManagement() {
            try {
                const response = await axios.get('/profile/users', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.usersList = response.data.users.map(user => {
                    let currentCost = 0;
                    let totalReservations = user.parking_stats?.total_reservations || 0;
                    let totalSpent = user.parking_stats?.total_amount_spent || 0;
    
                    const isCurrentlyParked = user.is_currently_parked || user.currently_parked || 
                                            (user.current_parking && user.current_parking.length > 0);
                    
                    if (isCurrentlyParked && user.current_parking && user.current_parking.length > 0) {
                    const currentParking = user.current_parking[0];
                    const hourlyRate = currentParking.lot_price || currentParking.price || 25;
                    let duration = currentParking.duration_hours || 0;
                    if (!duration && currentParking.parking_since) {
                        const parkingStart = new Date(currentParking.parking_since);
                        const now = new Date();
                        const diffInHours = (now - parkingStart) / (1000 * 60 * 60); // Convert ms to hours
                        duration = Math.max(0, diffInHours); 
                    }
                    
                    currentCost = Math.round((duration || 0) * (hourlyRate || 25) * 100) / 100;
                    if (totalReservations === 0) {
                        totalReservations = 1;
                    }
                }
                    return {
                        ...user,
                        total_reservations: totalReservations,
                        total_spent: totalSpent, 
                        current_cost: currentCost, 
                        currently_parked: isCurrentlyParked,
                        last_activity_days: isCurrentlyParked ? 0 : user.last_activity_days,
                        can_delete: !isCurrentlyParked && (user.last_activity_days > 30)
                    };
                });
                console.log('Users loaded for management:', this.usersList);
            } catch (error) {
                console.error('Users fetch error:', error);
                alert('Failed to load users: ' + (error.response?.data?.error || 'Network error'));
            }
        },

        getUserStatusBadge(user) {
            if (user.currently_parked) return 'badge bg-warning text-dark';
            if (!user.last_activity_days || user.last_activity_days <= 7) return 'badge bg-success';
            if (user.last_activity_days <= 30) return 'badge bg-secondary';
            return 'badge bg-danger';
        },

        getUserStatusText(user) {
            if (user.currently_parked) return 'Currently Parked';
            if (!user.last_activity_days || user.last_activity_days <= 7) return 'Active';
            if (user.last_activity_days <= 30) return 'Inactive';
            return 'Very Inactive';
        },

        async viewUserDetails(userId) {
            try {
                const response = await axios.get(`/profile/users/${userId}/details`, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.selectedUser = response.data.user;
                this.showUserDetailsModal = true;
            } catch (error) {
                console.error('User details fetch error:', error);
                alert('Failed to load user details: ' + (error.response?.data?.error || 'Network error'));
            }
        },

        confirmDeleteUser(user) {
            if (user.currently_parked) {
                alert('Cannot delete user with active parking session');
                return;
            }

            if (!user.can_delete) {
                alert('User must be inactive for 30+ days to be deleted');
                return;
            }

            this.userToDelete = user;
            this.deleteConfirmation = '';
            this.showDeleteModal = true;
        },

        async deleteUser() {
            if (this.deleteConfirmation !== 'DELETE') {
                alert('Please type DELETE to confirm');
                return;
            }
            try {
                await axios.delete(`/profile/users/${this.userToDelete.id}`, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                alert('User deleted successfully');
                this.showDeleteModal = false;
                this.userToDelete = null;
                this.deleteConfirmation = '';
                this.loadUsersForManagement();
            } catch (error) {
                console.error('User delete error:', error);
                alert('Failed to delete user: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },

        // PARKING LOT MANAGEMENT METHODS
        async fetchParkingLots() {
            try {
                const response = await axios.get('/admin/lots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingLots = response.data.lots || [];
            } catch (error) {
                console.error('Failed to fetch parking lots:', error);
                this.parkingLots = [];
            }
        },

        async fetchParkingSpots() {
            try {
                const response = await axios.get('/admin/spots', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.parkingSpots = response.data.spots || [];
            } catch (error) {
                console.error('Failed to fetch parking spots:', error);
                this.parkingSpots = [];
            }
        },

        async fetchUsers() {
            try {
                const response = await axios.get('/admin/users', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                this.users = response.data.users || [];
            } catch (error) {
                console.error('Failed to fetch users:', error);
                this.users = [];
            }
        },

        async createParkingLot() {
            if (!this.validateLotData()) {
                return;
            }
            try {
                await axios.post('/admin/lots', {
                    prime_location_name: this.newLot.prime_location_name,
                    price: parseFloat(this.newLot.price),
                    address: this.newLot.address,
                    pin_code: this.newLot.pin_code,
                    number_of_spots: parseInt(this.newLot.number_of_spots)
                }, {
                    headers: { 
                        Authorization: `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    }
                });
                alert('Parking lot created successfully!');
                this.showCreateLotModal = false;
                this.resetNewLot();
                await this.fetchParkingLots();
                await this.fetchDashboardSummary();
                await this.fetchOverviewData();
            } catch (error) {
                console.error('Create lot error:', error);
                alert('Failed to create lot: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },

        async viewLotDetails(lotId) {
            try {
                const response = await axios.get(`/admin/lots/${lotId}`, {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                const lotData = response.data.lot_details;
                
                if (!lotData.total_spots || !lotData.available_spots) {
                    const spotsResponse = await axios.get('/admin/spots', {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    
                    const allSpots = spotsResponse.data.spots || [];
                    const lotSpots = allSpots.filter(spot => spot.lot_id === lotId);
                    
                    lotData.total_spots = lotSpots.length;
                    lotData.available_spots = lotSpots.filter(spot => spot.status === 'A' || spot.status === 'available').length;
                    lotData.occupied_spots = lotSpots.filter(spot => spot.status === 'O' || spot.status === 'occupied').length;
                    lotData.occupancy_rate = lotData.total_spots > 0 ? 
                        Math.round((lotData.occupied_spots / lotData.total_spots) * 100) : 0;
                }
                
                this.selectedLotDetails = lotData;
                this.showViewModal = true;
            } catch (error) {
                console.error('View lot error:', error);
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
                await axios.put(`/admin/lots/${this.editLotData.id}`, {
                    prime_location_name: this.editLotData.prime_location_name,
                    price: parseFloat(this.editLotData.price),
                    address: this.editLotData.address,
                    pin_code: this.editLotData.pin_code,
                    number_of_spots: parseInt(this.editLotData.number_of_spots)
                }, {
                    headers: { 
                        Authorization: `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    }
                });
                
                this.showEditModal = false;
                await this.fetchParkingLots();
                await this.fetchDashboardSummary();
                await this.fetchOverviewData();
                alert('Parking lot updated successfully!');
            } catch (error) {
                console.error('Update lot error:', error);
                alert('Failed to update parking lot: ' + (error.response?.data?.error || 'Unknown error'));
            }
        },

        async deleteLot(lotId) {
            if (confirm('Are you sure you want to delete this parking lot?')) {
                try {
                    await axios.delete(`/admin/lots/${lotId}`, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    await this.fetchParkingLots();
                    await this.fetchDashboardSummary();
                    await this.fetchOverviewData();
                    alert('Parking lot deleted successfully!');
                } catch (error) {
                    alert('Failed to delete parking lot: ' + (error.response?.data?.error || 'Unknown error'));
                }
            }
        },

        validateLotData() {
            if (!this.newLot.prime_location_name?.trim()) {
                alert('Location name is required');
                return false;
            }
            if (!this.newLot.price || this.newLot.price <= 0) {
                alert('Valid price is required');
                return false;
            }
            if (!this.newLot.number_of_spots || this.newLot.number_of_spots <= 0) {
                alert('Number of spots must be greater than 0');
                return false;
            }
            return true;
        },

        resetNewLot() {
            this.newLot = {
                prime_location_name: '',
                price: '',
                address: '',
                pin_code: '',
                number_of_spots: ''
            };
        },

        async deleteIndividualSpot(spotId, spotInfo) {
            const confirmMessage = `Delete Spot ${spotId} from ${spotInfo.lot_name}?\n\nThis cannot be undone.`;
            if (confirm(confirmMessage)) {
                try {
                    await axios.delete(`/admin/spots/${spotId}/remove`, {
                        headers: { Authorization: `Bearer ${this.token}` }
                    });
                    await this.fetchParkingSpots();
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
                this.isLoading = true;
                const response = await axios.get('/analytics/admin/parking-stats', {
                    headers: { Authorization: `Bearer ${this.token}` }
                });
                
                this.analyticsData = response.data;
                this.updateSummaryCards();
                this.lastUpdated = new Date().toLocaleTimeString('en-IN');
                
                await this.$nextTick();
                this.createModernCharts();
                
            } catch (error) {
                console.error('Analytics fetch failed:', error);
                this.analyticsData = {
                    daily_activity: [{ date: 'Today', reservations: 0, revenue: 0 }],
                    lot_status: [{ name: 'No Data', occupied: 0, available: 1, occupancy: 0 }],
                    revenue_trends: [{ period: 'Today', amount: 0 }],
                    peak_hours: [{ hour: '12:00', bookings: 0 }],
                    summary: { total_lots: 0, total_spots: 0, active_users: 0, today_revenue: 0 }
                };
                this.updateSummaryCards();
                await this.$nextTick();
                this.createModernCharts();
            } finally {
                this.isLoading = false;
            }
        },

        updateSummaryCards() {
            if (!this.analyticsData?.summary) return;
            
            const s = this.analyticsData.summary;
            this.summaryCards = [
                { title: 'Total Parking Lots', value: s.total_lots, icon: 'fas fa-building', color: 'primary' },
                { title: 'Total Parking Spots', value: s.total_spots, icon: 'fas fa-car', color: 'success' },
                { title: 'Active Users', value: s.active_users, icon: 'fas fa-users', color: 'warning' },
                { title: 'Today\'s Revenue', value: `₹${s.today_revenue}`, icon: 'fas fa-rupee-sign', color: 'info' }
            ];
        },

        createModernCharts() {
            this.destroyExistingCharts();
            if (!this.analyticsData) return;

            const commonOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true } }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                    x: { grid: { color: 'rgba(0,0,0,0.05)' } }
                }
            };

            // Weekly Activity Chart 
            const weeklyCanvas = document.getElementById('weeklyActivityChart');
            if (weeklyCanvas) {
                this.chartInstances.weekly = new Chart(weeklyCanvas, {
                    type: 'bar',
                    data: {
                        labels: this.analyticsData.daily_activity.map(d => d.date),
                        datasets: [{
                            label: 'Reservations',
                            data: this.analyticsData.daily_activity.map(d => d.reservations),
                            backgroundColor: 'rgba(102, 126, 234, 0.8)',
                            borderColor: 'rgba(102, 126, 234, 1)',
                            borderWidth: 2,
                            borderRadius: 8
                        }, {
                            label: 'Revenue (₹)',
                            data: this.analyticsData.daily_activity.map(d => d.revenue),
                            type: 'line',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            backgroundColor: 'rgba(255, 99, 132, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: commonOptions
                });
            }

            // Live Occupancy Chart
            const occupancyCanvas = document.getElementById('occupancyChart');
            if (occupancyCanvas) {
                this.chartInstances.occupancy = new Chart(occupancyCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: this.analyticsData.lot_status.map(l => l.name),
                        datasets: [{
                            data: this.analyticsData.lot_status.map(l => l.occupancy),
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.8)', 'rgba(54, 162, 235, 0.8)',
                                'rgba(255, 205, 86, 0.8)', 'rgba(75, 192, 192, 0.8)',
                                'rgba(153, 102, 255, 0.8)', 'rgba(255, 159, 64, 0.8)'
                            ],
                            borderWidth: 3,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'right' },
                            tooltip: {
                                callbacks: {
                                    label: (context) => `${context.label}: ${context.parsed}% occupied`
                                }
                            }
                        }
                    }
                });
            }

            // Revenue Analysis Chart 
            const revenueCanvas = document.getElementById('revenueChart');
            if (revenueCanvas) {
                this.chartInstances.revenue = new Chart(revenueCanvas, {
                    type: 'bar',
                    data: {
                        labels: this.analyticsData.revenue_trends.map(r => r.period),
                        datasets: [{
                            label: 'Revenue (₹)',
                            data: this.analyticsData.revenue_trends.map(r => r.amount),
                            backgroundColor: (ctx) => {
                                const canvas = ctx.chart.ctx;
                                const gradient = canvas.createLinearGradient(0, 0, 0, 400);
                                gradient.addColorStop(0, 'rgba(102, 126, 234, 0.8)');
                                gradient.addColorStop(1, 'rgba(118, 75, 162, 0.8)');
                                return gradient;
                            },
                            borderRadius: 12,
                            borderSkipped: false
                        }]
                    },
                    options: { 
                        ...commonOptions, 
                        plugins: { ...commonOptions.plugins, legend: { display: false } } 
                    }
                });
            }

            // Peak Hours Chart
            const peakHoursCanvas = document.getElementById('peakHoursChart');
            if (peakHoursCanvas) {
                this.chartInstances.peakHours = new Chart(peakHoursCanvas, {
                    type: 'polarArea',
                    data: {
                        labels: this.analyticsData.peak_hours.map(p => p.hour),
                        datasets: [{
                            data: this.analyticsData.peak_hours.map(p => p.bookings),
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.6)', 'rgba(54, 162, 235, 0.6)',
                                'rgba(255, 205, 86, 0.6)', 'rgba(75, 192, 192, 0.6)',
                                'rgba(153, 102, 255, 0.6)'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'bottom' } }
                    }
                });
            }
        },

        destroyExistingCharts() {
            Object.values(this.chartInstances).forEach(chart => {
                if (chart) chart.destroy();
            });
            this.chartInstances = {};
        },

        async refreshAnalytics() {
            await this.fetchAnalytics();
        },

        async triggerCSVExport(exportType = 'admin') {
            try {
                this.exportStatus = 'processing';
                
                const response = await axios.get('/admin/export/csv/direct', {
                    headers: { Authorization: `Bearer ${this.token}` },
                    responseType: 'blob'
                });
                
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.download = `admin_parking_export_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
                
                this.exportStatus = '';
                alert('Admin CSV exported successfully!');
                
            } catch (error) {
                console.error('Admin CSV export failed:', error);
                this.exportStatus = '';
                alert('Failed to export admin CSV: ' + (error.response?.data?.error || 'Unknown error'));
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
                    this.downloadCSV();
                } else if (response.data.state === 'FAILURE') {
                    alert('Export failed: ' + response.data.error);
                    this.exportStatus = '';
                } else {
                    setTimeout(() => this.checkExportStatus(), 2000);
                }
            } catch (error) {
                console.error('Failed to check export status:', error);
                this.exportStatus = '';
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
                alert('CSV file downloaded successfully!');
            } catch (error) {
                alert('Failed to download CSV');
                this.exportStatus = '';
            }
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

        formatDateTime(dateString) {
            if (!dateString) return '-';
            return new Date(dateString).toLocaleString('en-IN');
        }
    }
}).mount('#app');

