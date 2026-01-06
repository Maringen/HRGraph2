import React, { useEffect, useRef, useState, useCallback } from 'react';
import G6 from '@antv/g6';

/**
 * HRGraphView - AntV G6 component for visualizing HR Knowledge Graph
 * 
 * Features:
 * - Interactive graph with drag-canvas, zoom-canvas, drag-node, activate-relations
 * - Combo grouping by Department for Employee nodes
 * - Multiple layouts: force/gForce (network), compactBox/dendrogram (org chart)
 * - TimeBar plugin for temporal filtering
 * - API integration with G6-formatted data
 */
interface HRGraphViewProps {
  apiUrl?: string;
  apiKey?: string;
  height?: number | string;
  onNodeClick?: (node: any) => void;
  onEdgeClick?: (edge: any) => void;
}

interface G6Node {
  id: string;
  label: string;
  comboId?: string;
  nodeType: string;
  data?: Record<string, any>;
}

interface G6Edge {
  id: string;
  source: string;
  target: string;
  label?: string;
  relation?: string;
  data?: Record<string, any>;
}

interface G6Combo {
  id: string;
  label: string;
}

interface GraphData {
  nodes: G6Node[];
  edges: G6Edge[];
  combos?: G6Combo[];
  valid_at?: string;
  expired_at?: string;
}

const HRGraphView: React.FC<HRGraphViewProps> = ({
  apiUrl = '/graph',
  apiKey = '',
  height = 600,
  onNodeClick,
  onEdgeClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<G6.Graph | null>(null);
  const [currentLayout, setCurrentLayout] = useState<'force' | 'compactBox' | 'dendrogram'>('force');
  const [showTimeBar, setShowTimeBar] = useState(true);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);

  // Node type configuration
  const nodeConfig: Record<string, { color: string; size: number; shape: string }> = {
    Employee: { color: '#667eea', size: 30, shape: 'circle' },
    Position: { color: '#ff9800', size: 26, shape: 'ellipse' },
    Department: { color: '#4caf50', size: 35, shape: 'circle' },
    Project: { color: '#e91e63', size: 28, shape: 'rect' },
    Skill: { color: '#00bcd4', size: 22, shape: 'circle' },
  };

  // Edge configuration
  const edgeConfig: Record<string, { color: string; width: number }> = {
    PROFICIENT_IN: { color: '#667eea', width: 2 },
    WORKS_IN: { color: '#4caf50', width: 2 },
    BELONGS_TO: { color: '#ff9800', width: 2 },
    REPORTS_TO: { color: '#e91e63', width: 2 },
    WORKS_ON: { color: '#00bcd4', width: 2 },
    COLLABORATES_WITH: { color: '#9c27b0', width: 2 },
    MANAGES: { color: '#f44336', width: 2 },
    default: { color: '#ccc', width: 1 },
  };

  // Node classification function
  const getNodeType = useCallback((label: string): string => {
    const l = label.toLowerCase().trim();
    
    // Name substrings check
    const nameSubstrings = ['john', 'smith', 'jones', 'williams', 'brown', 'davis', 'miller', 'wilson', 'moore', 'taylor', 'anderson', 'thomas', 'jackson', 'white', 'harris', 'martin', 'thompson', 'garcia', 'martinez', 'robinson', 'clark', 'rodriguez', 'lewis', 'lee', 'walker', 'hall', 'allen', 'young', 'hernandez', 'king', 'wright', 'lopez', 'hill', 'scott', 'green', 'adams', 'baker', 'nelson', 'carter', 'mitchell', 'perez', 'roberts', 'turner', 'phillips', 'campbell', 'parker', 'evans', 'edwards', 'collins', 'stewart', 'sanchez', 'morris', 'murphy', 'cook', 'rogers', 'gutierrez', 'ortiz', 'morgan', 'cooper', 'peterson', 'bailey', 'reed', 'kelly', 'howard', 'ramos', 'kim', 'cox', 'ward', 'richardson', 'watson', 'brooks', 'chavez', 'wood', 'james', 'bennett', 'gray', 'mendoza', 'ruiz', 'hughes', 'price', 'alvarez', 'castillo', 'sanders', 'patel', 'myers', 'ross', 'foster', 'jimenez', 'powell', 'jenkins', 'perry', 'russell', 'sullivan', 'bell', 'coleman', 'butler', 'henderson', 'barnes', 'gonzales', 'fisher', 'vasquez', 'simmons', 'romero', 'jordan', 'patterson', 'alexander', 'hamilton', 'graham'];
    
    if (l in nameSubstrings) return 'Employee';
    
    const departments = ['engineering', 'human resources', 'sales', 'marketing', 'finance', 'hr', 'it', 'operations', 'legal', 'design', 'product', 'research'];
    if (departments.includes(l) || l.includes('department')) return 'Department';
    
    const positionTitles = ['cto', 'cfo', 'ceo', 'coo', 'cio', 'cmo'];
    if (positionTitles.includes(l)) return 'Position';
    if (l === 'auditor' || l === 'analyst' || l === 'architect') return 'Position';
    
    if (l.includes('project') || l.includes('campaign')) return 'Project';
    
    const techSkills = ['python', 'javascript', 'java', 'go', 'react', 'node', 'aws', 'kubernetes', 'docker', 'tensorflow', 'machine learning', 'data science'];
    if (techSkills.some(skill => l.includes(skill))) return 'Skill';
    
    const softSkills = ['leadership', 'communication', 'management', 'agile', 'scrum', 'negotiation'];
    if (softSkills.some(skill => l.includes(skill))) return 'Skill';
    
    if (l.includes('position') || l.includes('engineer') || l.includes('manager') || l.includes('director') || l.includes('analyst') || l.includes('developer') || l.includes('consultant') || l.includes('specialist') || l.includes('supervisor') || l.includes('administrator') || l.includes('assistant') || l.includes('lead') || l.includes('head') || l.includes('senior') || l.includes('junior') || l.includes('rep')) {
      return 'Position';
    }
    
    const words = l.split(' ').filter(w => w.length > 0);
    if (words.length >= 2 && words.length <= 4) {
      return 'Employee';
    }
    
    return 'Skill';
  }, []);

  // Format data for G6 from raw API data
  const formatForG6 = useCallback((data: any): GraphData => {
    const nodes: G6Node[] = [];
    const edges: G6Edge[] = [];
    const combos = new Set<string>();
    const seenNodes = new Set<string>();

    // Process nodes
    data.nodes?.forEach((node: any) => {
      const nodeId = String(node.id);
      if (!seenNodes.has(nodeId)) {
        const type = node.labels?.[0] || getNodeType(node.label);
        const config = nodeConfig[type] || nodeConfig.Employee;
        
        // Get department for combo grouping
        let comboId = 'Inconnu';
        if (type === 'Employee') {
          // Find the department through WORKS_IN relationship
          const deptEdge = data.edges?.find((e: any) => 
            (e.source === nodeId || e.source === node.id) && e.label === 'BELONGS_TO'
          );
          if (deptEdge) {
            const deptNode = data.nodes?.find((n: any) => String(n.id) === String(deptEdge.target));
            comboId = deptNode?.label || 'Inconnu';
          }
        }
        
        nodes.push({
          id: nodeId,
          label: node.label,
          comboId: type === 'Employee' ? comboId : undefined,
          nodeType: type,
          data: node.properties || {},
        });
        
        if (type === 'Employee') {
          combos.add(comboId);
        }
        
        seenNodes.add(nodeId);
      }
    });

    // Process edges
    data.edges?.forEach((edge: any, index: number) => {
      const config = edgeConfig[edge.label] || edgeConfig.default;
      edges.push({
        id: String(edge.id || `e${index}`),
        source: String(edge.source),
        target: String(edge.target),
        label: edge.label,
        relation: edge.label,
        data: edge.properties || {},
      });
    });

    // Create combo list
    const comboList: G6Combo[] = Array.from(combos).map(dept => ({
      id: dept,
      label: dept,
    }));

    return {
      nodes,
      edges,
      combos: comboList.length > 0 ? comboList : undefined,
      valid_at: data.valid_at,
      expired_at: data.expired_at,
    };
  }, [getNodeType, nodeConfig]);

  // Fetch graph data from API
  const fetchGraphData = useCallback(async (date?: string) => {
    setLoading(true);
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (apiKey) {
        headers['Authorization'] = `Bearer ${apiKey}`;
      }

      const url = date ? `${apiUrl}?valid_at=${encodeURIComponent(date)}` : apiUrl;
      const response = await fetch(url, { headers });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      const formattedData = formatForG6(data);
      setGraphData(formattedData);
      
      if (selectedDate === '') {
        setSelectedDate(data.valid_at || '');
      }
    } catch (error) {
      console.error('Error fetching graph data:', error);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, apiKey, formatForG6, selectedDate]);

  // Initialize G6 graph
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth || 800;
    const heightValue = typeof height === 'number' ? height : container.clientHeight || 600;

    // Register combo styles
    G6.registerCombo('department-combo', {
      draw(cfg: any, group: any) {
        const style = cfg.style || {};
        return group.addShape('rect', {
          attrs: {
            x: cfg.x,
            y: cfg.y,
            width: cfg.size?.width || 200,
            height: cfg.size?.height || 100,
            fill: style.fill || '#f0f5ff',
            stroke: style.stroke || '#adc6ff',
            radius: 8,
            lineWidth: 2,
          },
          name: 'combo-key-shape',
        });
      },
    });

    // Create graph instance
    const graph = new G6.Graph({
      container: 'graph-container',
      width: width,
      height: heightValue,
      fitView: true,
      fitViewPadding: 30,
      animate: true,
      defaultNode: {
        type: 'circle',
        labelCfg: {
          position: 'bottom',
          offset: 5,
          style: {
            fontSize: 11,
            fill: '#333',
          },
        },
      },
      defaultCombo: {
        type: 'department-combo',
        labelCfg: {
          position: 'top',
          style: {
            fontSize: 12,
            fill: '#333',
            fontWeight: 'bold',
          },
        },
      },
      defaultEdge: {
        type: 'cubic',
        labelCfg: {
          autoRotate: true,
          style: {
            fontSize: 9,
            fill: '#666',
          },
        },
      },
      modes: {
        default: [
          'drag-canvas',
          'zoom-canvas',
          'drag-node',
          'drag-combo',
          'activate-relations',
          'click-select',
        ],
      },
      nodeStateStyles: {
        hover: {
          lineWidth: 3,
          shadowColor: '#667eea',
          shadowBlur: 10,
        },
        selected: {
          lineWidth: 4,
          stroke: '#667eea',
        },
      },
      edgeStateStyles: {
        hover: {
          lineWidth: 3,
          opacity: 1,
        },
        inactive: {
          opacity: 0.2,
        },
      },
      layout: {
        type: currentLayout === 'force' ? 'gForce' : currentLayout,
        preventOverlap: true,
        nodeSpacing: 50,
        linkDistance: 150,
        nodeStrength: -300,
        edgeStrength: 0.1,
        comboCollideStrength: 0.8,
        comboSpacing: 20,
        onTick: () => {
          // Layout tick callback
        },
      },
      plugins: [
        // TimeBar plugin will be added when showTimeBar is true
      ] as any,
    });

    graphRef.current = graph;

    // Event handlers
    graph.on('node:mouseenter', (e: any) => {
      graph.setItemState(e.item, 'hover', true);
      // Activate connected edges
      const edges = e.item.getEdges();
      edges.forEach((edge: any) => {
        graph.setItemState(edge, 'hover', true);
      });
    });

    graph.on('node:mouseleave', (e: any) => {
      graph.setItemState(e.item, 'hover', false);
      const edges = e.item.getEdges();
      edges.forEach((edge: any) => {
        graph.setItemState(edge, 'hover', false);
      });
    });

    graph.on('node:click', (e: any) => {
      const model = e.item.getModel();
      onNodeClick?.(model);
    });

    graph.on('edge:click', (e: any) => {
      const model = e.item.getModel();
      onEdgeClick?.(model);
    });

    // Handle window resize
    const handleResize = () => {
      if (graphRef.current && containerRef.current) {
        graphRef.current.changeSize(
          containerRef.current.clientWidth,
          containerRef.current.clientHeight
        );
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      graph.destroy();
    };
  }, [height, currentLayout, onNodeClick, onEdgeClick]);

  // Update graph data when it changes
  useEffect(() => {
    if (!graphRef.current || !graphData) return;

    const nodes = graphData.nodes.map(node => {
      const config = nodeConfig[node.nodeType] || nodeConfig.Employee;
      return {
        id: node.id,
        label: node.label,
        comboId: node.comboId,
        nodeType: node.nodeType,
        size: config.size,
        style: {
          fill: config.color,
          stroke: config.color,
          lineWidth: 2,
        },
        data: node.data,
      };
    });

    const edges = graphData.edges.map(edge => {
      const config = edgeConfig[edge.label || ''] || edgeConfig.default;
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        style: {
          stroke: config.color,
          lineWidth: config.width,
          endArrow: true,
        },
        data: edge.data,
      };
    });

    const combos = graphData.combos?.map(combo => ({
      id: combo.id,
      label: combo.label,
      style: {
        fill: '#f0f5ff',
        stroke: '#adc6ff',
      },
    }));

    graphRef.current.data({
      nodes,
      edges,
      combos,
    });
    graphRef.current.render();
    graphRef.current.fitView(30);
  }, [graphData, nodeConfig, edgeConfig]);

  // Fetch data on mount
  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  // Toggle layout
  const toggleLayout = () => {
    const layouts: Array<'force' | 'compactBox' | 'dendrogram'> = ['force', 'compactBox', 'dendrogram'];
    const currentIndex = layouts.indexOf(currentLayout);
    const nextLayout = layouts[(currentIndex + 1) % layouts.length];
    setCurrentLayout(nextLayout);

    if (graphRef.current) {
      if (nextLayout === 'force') {
        graphRef.current.updateLayout({
          type: 'gForce',
          preventOverlap: true,
          nodeSpacing: 50,
          linkDistance: 150,
          nodeStrength: -300,
          edgeStrength: 0.1,
        });
      } else {
        graphRef.current.updateLayout({
          type: nextLayout,
          direction: 'TB',
          getId: (d: any) => d.id,
          getHeight: () => 16,
          getWidth: () => 16,
          getVGap: () => 100,
          getHGap: () => 50,
        });
      }
      graphRef.current.layout();
    }
  };

  // Fit view
  const handleFitView = () => {
    graphRef.current?.fitView(30);
  };

  // Zoom controls
  const handleZoomIn = () => {
    const zoom = graphRef.current?.getZoom() || 1;
    graphRef.current?.zoomTo(zoom * 1.2);
  };

  const handleZoomOut = () => {
    const zoom = graphRef.current?.getZoom() || 1;
    graphRef.current?.zoomTo(zoom / 1.2);
  };

  // Toggle TimeBar
  const handleToggleTimeBar = () => {
    setShowTimeBar(!showTimeBar);
    // Re-render graph to apply/remove TimeBar plugin
  };

  return (
    <div style={{ width: '100%', height: typeof height === 'number' ? height : 'auto' }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex',
        gap: '10px',
        padding: '10px',
        background: '#f8f9fa',
        borderBottom: '1px solid #eee',
        flexWrap: 'wrap',
        alignItems: 'center',
      }}>
        <button
          onClick={handleFitView}
          style={{
            padding: '8px 16px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
          }}
        >
          Fit View
        </button>
        
        <button
          onClick={toggleLayout}
          style={{
            padding: '8px 16px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
          }}
        >
          Layout: {currentLayout === 'force' ? 'Network' : currentLayout === 'compactBox' ? 'Org Chart' : 'Dendrogram'}
        </button>
        
        <button
          onClick={handleZoomIn}
          style={{
            padding: '8px 16px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
          }}
        >
          Zoom +
        </button>
        
        <button
          onClick={handleZoomOut}
          style={{
            padding: '8px 16px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
          }}
        >
          Zoom -
        </button>
        
        <button
          onClick={handleToggleTimeBar}
          style={{
            padding: '8px 16px',
            background: showTimeBar ? '#4caf50' : '#ff9800',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
          }}
        >
          TimeBar {showTimeBar ? 'ON' : 'OFF'}
        </button>

        <input
          type="date"
          value={selectedDate}
          onChange={(e) => {
            setSelectedDate(e.target.value);
            fetchGraphData(e.target.value);
          }}
          style={{
            padding: '8px 12px',
            border: '2px solid #ddd',
            borderRadius: '6px',
            fontSize: '13px',
          }}
        />

        {loading && <span style={{ color: '#666' }}>Loading...</span>}
      </div>

      {/* Graph Container */}
      <div
        ref={containerRef}
        id="graph-container"
        style={{
          width: '100%',
          height: typeof height === 'number' ? height - 50 : 'calc(100% - 50px)',
          background: '#fafafa',
        }}
      />

      {/* Legend */}
      <div style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        background: 'white',
        padding: '15px',
        borderRadius: '8px',
        boxShadow: '0 4px 15px rgba(0,0,0,0.15)',
        zIndex: 100,
      }}>
        <h4 style={{ marginBottom: '10px', fontSize: '14px' }}>Legend</h4>
        {Object.entries(nodeConfig).map(([type, config]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '6px 0', fontSize: '12px' }}>
            <div style={{
              width: '16px',
              height: '16px',
              borderRadius: type === 'Position' ? '4px' : '50%',
              background: config.color,
            }} />
            {type}
          </div>
        ))}
      </div>
    </div>
  );
};

export default HRGraphView;
