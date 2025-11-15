
class RoleHierarchyManager {
  constructor() {
    this.orgChart = null;
    this.rolesData = null;
    this.urls = {
      addUserToRoles: null,
      createRoles: null,
      viewUserInRole: null
    };

    this.init();
  }

  init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      this.setup();
    }
  }

  setup() {
    // Get data and URLs from data attributes or global variables
    this.loadConfiguration();

    if (!this.rolesData) {
      console.error('Roles data not found. Please ensure data is properly loaded.');
      return;
    }

    this.initializeOrgChart();
    this.setupEventListeners();
  }

  loadConfiguration() {
    // Try to get data from various sources

    // Method 1: From global window variable (if set by Django template)
    if (window.rolesData) {
      this.rolesData = window.rolesData;
    }

    // Method 2: From data attributes on the container
    const container = document.getElementById('role-container');
    if (container) {
      if (container.dataset.rolesData) {
        try {
          this.rolesData = JSON.parse(container.dataset.rolesData);
        } catch (e) {
          console.error('Error parsing roles data:', e);
        }
      }

      // Get URLs from data attributes
      this.urls.addUserToRoles = container.dataset.addUserUrl;
      this.urls.createRoles = container.dataset.createRoleUrl;
      this.urls.viewUserInRole = container.dataset.viewUserUrl;
    }

    // Method 3: Make an AJAX call to fetch data if not available
    if (!this.rolesData) {
      this.fetchRolesData();
    }
  }

  async fetchRolesData() {
    try {
      const response = await fetch('/api/roles-hierarchy/'); // Adjust URL as needed
      if (response.ok) {
        this.rolesData = await response.json();
        this.initializeOrgChart();
      }
    } catch (error) {
      console.error('Failed to fetch roles data:', error);
    }
  }

  initializeOrgChart() {
    if (!this.rolesData || !window.OrgChart) {
      console.error('Missing dependencies: rolesData or OrgChart library');
      return;
    }

    // Clear existing chart
    if (this.orgChart && this.orgChart.destroy) {
      this.orgChart.destroy();
    }

    // Clear the tree container
    const treeElement = document.getElementById('tree');
    if (treeElement) {
      treeElement.innerHTML = '';
    }

    // Configure OrgChart template
    this.configureOrgChartTemplate();

    // Create chart
    this.orgChart = new OrgChart("#tree", {
      nodeBinding: {
        field_0: "name",
      },
      tags: {
        primary: { template: "primary" },
      },
      enableSearch: false,
      toolbar: false,
      editForm: {
        readOnly: true,
        generateElementsFromFields: false,
      },
      nodeMouseClick: OrgChart.action.none,
      nodes: this.rolesData,
    });

    return this.orgChart;
  }

  configureOrgChartTemplate() {
    // EXACT original template configuration
    OrgChart.templates.primary = Object.assign({}, OrgChart.templates.ana);

    OrgChart.templates.primary.node = `
      <rect x="0" y="0" height="95" width="230" fill="#e54f381a" stroke="#e54f38bd" stroke-width="1" rx="12" ry="12"></rect>
    `;

    // Fixed field_0 with bold font-weight and proper font-size
    OrgChart.templates.primary.field_0 = `
      <text class="field_0" x="115" y="45" text-anchor="middle" font-weight="bold" font-size="16px" fill="#333">{val}</text>
    `;

    OrgChart.templates.primary.icons = `
    <g transform="translate(130, 65)" style="cursor:pointer;" data-node-id="{val}">
      <!-- User icon -->
      <g class="user-icon" transform="translate(0, 0)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="#ff8c2e">
          <path d="M12 12c2.7 0 5-2.3 5-5s-2.3-5-5-5-5 2.3-5 5 2.3 5 5 5zm0 2c-3.3 0-10 1.7-10 5v3h20v-3c0-3.3-6.7-5-10-5z"/>
        </svg>
      </g>

      <!-- Plus icon -->
      <g class="plus-icon" transform="translate(30, 0)">
        <svg width="18" height="18" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" fill="#ff8c2e"></circle>
          <line x1="12" y1="7" x2="12" y2="17" stroke="white" stroke-width="2"></line>
          <line x1="7" y1="12" x2="17" y2="12" stroke="white" stroke-width="2"></line>
        </svg>
      </g>

      <!-- Eye icon -->
      <g class="view-icon" transform="translate(62, -3)">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="#ff8c2e">
          <path d="M12 5c-7 0-11 7-11 7s4 7 11 7 11-7 11-7-4-7-11-7zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-8a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"/>
        </svg>
      </g>
    </g>
    `;

    OrgChart.templates.primary.node += OrgChart.templates.primary.icons;
  }

  setupEventListeners() {
    // Handle icon clicks
    document.addEventListener('click', (e) => {
      const nodeElement = e.target.closest('[data-n-id]');
      if (!nodeElement) return;

      const roleId = nodeElement.getAttribute('data-n-id');

      if (e.target.closest('.user-icon')) {
        this.handleUserIconClick(roleId);
      } else if (e.target.closest('.plus-icon')) {
        this.handlePlusIconClick(roleId);
      } else if (e.target.closest('.view-icon')) {
        this.handleViewIconClick(roleId);
      }
    });

    // Handle HTMX updates
    if (typeof htmx !== 'undefined') {
      document.addEventListener('htmx:afterSettle', (evt) => {
        if (evt.detail.target.querySelector('#tree') || evt.detail.target.id === 'tree') {
          setTimeout(() => {
            this.initializeOrgChart();
          }, 150);
        }
      });
    }

    // Handle page navigation events
    window.addEventListener('popstate', () => {
      setTimeout(() => this.reinitialize(), 100);
    });
  }

  handleUserIconClick(roleId) {
    if (typeof htmx !== 'undefined' && this.urls.addUserToRoles) {
      htmx.ajax('GET', this.urls.addUserToRoles, {
        target: '#modalBox',
        values: { role_id: roleId },
        swap: 'innerHTML'
      }).then(() => {
        if (typeof openModal === 'function') {
          openModal();
        }
      });
    } else {
      // Fallback for non-HTMX environments
      this.openUserModal(roleId);
    }
  }

  handlePlusIconClick(roleId) {
    if (typeof htmx !== 'undefined' && this.urls.createRoles) {
      htmx.ajax('GET', this.urls.createRoles, {
        target: '#modalBox',
        values: { role_id: roleId },
        swap: 'innerHTML'
      }).then(() => {
        if (typeof openModal === 'function') {
          openModal();
        }
      });
    } else {
      // Fallback for non-HTMX environments
      this.openCreateRoleModal(roleId);
    }
  }

  handleViewIconClick(roleId) {
    if (typeof htmx !== 'undefined' && this.urls.viewUserInRole) {
      htmx.ajax('GET', this.urls.viewUserInRole, {
        target: '#contentModalBox',
        values: { role_id: roleId },
        swap: 'innerHTML'
      }).then(() => {
        if (typeof openContentModal === 'function') {
          openContentModal();
        }
      });
    } else {
      // Fallback for non-HTMX environments
      this.openViewModal(roleId);
    }
  }

  // Fallback methods for non-HTMX environments
  openUserModal(roleId) {
    console.log('Opening user modal for role:', roleId);
    // Implement your fallback logic here
  }

  openCreateRoleModal(roleId) {
    console.log('Opening create role modal for role:', roleId);
    // Implement your fallback logic here
  }

  openViewModal(roleId) {
    console.log('Opening view modal for role:', roleId);
    // Implement your fallback logic here
  }

  reinitialize() {
    this.loadConfiguration();
    if (this.rolesData) {
      this.initializeOrgChart();
    }
  }

  // Public method to refresh data and chart
  refresh(newData = null) {
    if (newData) {
      this.rolesData = newData;
    }
    this.initializeOrgChart();
  }

  // Public method to destroy the chart
  destroy() {
    if (this.orgChart && this.orgChart.destroy) {
      this.orgChart.destroy();
    }
  }
}

// Initialize the role hierarchy manager
let roleHierarchyManager;

// Initialize when the script loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    roleHierarchyManager = new RoleHierarchyManager();
  });
} else {
  roleHierarchyManager = new RoleHierarchyManager();
}

// Make it globally available
window.roleHierarchyManager = roleHierarchyManager;
