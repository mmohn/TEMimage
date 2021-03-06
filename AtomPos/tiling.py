"""
  Tiling of 2D space and its dual graph (Delaunay triangulation
  and Voronoi diagram)

  USAGE
    An example can be found at the end of this file and can be executed
     using 'python tiling.py'

  Copyright (c) 2013, rhambach. 
    This file is part of the FitAtomPos package and released
    under the MIT-Licence. See LICENCE file for details.
"""
import numpy as np;
import matplotlib.pylab as plt
import matplotlib.collections as c;

class Tiling:
  """
    Represents an tiling of the 2D space. By default, a Delaunay 
    triangulation is used to construct a tiling from the given points. 
    Alternatively, you can specify tiles and neighbors explicitly.
  """

  def __init__(self,points,vertices=None,neighbors=None,edges=None):
    """
      points   ... array(npoints,dim) for the vertices in the tiling
      vertices ... (opt) list(ntiles) of vertices for each tile
      neighbors... (opt) list(ntiles) of neighbors for each tile
      edges    ... (opt) list(nedges) of all edges
    """
    # points
    self.points = np.asarray(points,dtype=float);
    assert( self.points.ndim==2 and self.points.shape[1]==2 );

    # vertices,neighbors,edges
    if vertices is not None:
      self.vertices = [ self.sort_clockwise(v) for v in vertices ];
      self.neighbors= neighbors;
      self.edges    = edges;

    else:  # Delaunay triangulation
      from scipy.spatial import Delaunay;
      tri = Delaunay(points);
      self.vertices = tri.vertices.tolist();
      self.neighbors= tri.neighbors.tolist();
      self.edges = [];
      for v in self.vertices:
        for e in self.get_edges_of_tile(self.sort_clockwise(v)):
          if e[1]>e[0]: self.edges.append(e);

    self.edges = np.asarray(self.edges,dtype=int);
    self.ntiles = len(self.vertices);
    self.nedges = len(self.edges);
    self.npoints= self.points.shape[0];

  def sort_clockwise(self,vertices):
    " return list of vertices sorted clockwise "
    p = self.points[vertices];
    delta=p-np.mean(p,axis=0);   # vectors from mass center to each vertex point
                                 # sort using angle to x-axis
    return np.asarray(vertices)[ np.argsort(np.arctan2(*tuple(delta.T))) ];

  def get_edges_of_tile(self,sorted_vertices):
    " return list(nedges,2) of point indices for edges of a tile"
    edges=zip(sorted_vertices[:-1], sorted_vertices[1:]);
    edges.append((sorted_vertices[-1], sorted_vertices[0]));
    return edges;

  def get_dual(self):
    """ 
     return the dual graph of the tiling, which is constructed
      by mapping tile -> point of mass, points -> tiles
    """
    dpoints = []; dedges = []; 
    dneighbors = [[] for i in range(self.npoints)];
    dvertices  = [[] for i in range(self.npoints)];

    for t in range(self.ntiles):
      # center of mass for each polygon (dual to Delaunay face)
      dpoints.append(np.mean(self.points[self.vertices[t]],axis=0));
      # new edges connecting center of mass for all neighboring polygons
      for n in self.neighbors[t]:
        if 0<=n<t: dedges.append([t, n]); # avoid double counting
      # vertices of tile t <-> new tiles that have center of t as vertex
      for v in self.vertices[t]:
          dvertices[v].append(t); 

    # new neighbors are connected via an edge with t
    for i,j in self.edges:
      dneighbors[i].append(j);
      dneighbors[j].append(i);

    return Tiling(dpoints, dvertices, dneighbors, dedges);

  def flip(self, edge):
    """
    flip common edge between two triangles and update tiling
                         edge:          p1, p2
          A    p1  B     tile:          t1=(p1,p2,e1), t2=(p1,p2,e2)
             / | \       neighbors:     n1=(t2,A,D),   n2=(t1,B,C)
          e1 ..... e2    new_edge:      e1, e2
             \ | /       new_tile:      t1=(e1,e2,p1), t2=(e1,e2,p2)
          D    p2  C     new_neighobrs: n1=(t2,A,B),   n2=(t1,D,C)
    """

    p1,p2 = self.edges[edge];

    # find the two tiles that contain both vertices of the edge
    tiles=[]; new_edge=[]
    for t in range(self.ntiles):
      v     = np.asarray(self.vertices[t]);
      if len(v)!= 3: continue;   # only consider triangles
      index = (v==p1) | (v==p2); # boolean index array 
      if index.sum()==2:         # edge is part of tile t
        tiles.append(t); 
        new_edge.append(v[~index][0]);  # -> e1, e2
    if len(tiles)<>2: 
      print "FLIP: edge is not part of two triangles"; return;
    t1,t2 = tiles; e1,e2 = new_edge;

    # new neighbors for tiles t1, t2, D, B
    for n in self.neighbors[t1]:
      if p2 not in self.vertices[n]: A=n;
      if p1 not in self.vertices[n]: D=n;
    for n in self.neighbors[t2]:
      if p2 not in self.vertices[n]: B=n;
      if p1 not in self.vertices[n]: C=n;
    self.neighbors[t1] = [t2,A,B];
    self.neighbors[t2] = [t1,C,D];
    self.neighbors[D]  = [t2 if n==t1 else n for n in self.neighbors[D]];
    self.neighbors[B]  = [t1 if n==t2 else n for n in self.neighbors[B]];
    
    # new tiles (e1,e2,p1), (e1,e2,p2)
    self.vertices[t1] = self.sort_clockwise([e1,e2,p1]);
    self.vertices[t2] = self.sort_clockwise([e1,e2,p2]);
    
    # new edge
    self.edges[edge] = [e1,e2];


  def plot_vertices(self, ax=None, fc='red'):
    " plot points using matplotlib "
    if ax is None: plt.figure(); ax=plt.subplot(111);
    ax.plot(self.points[:,0], self.points[:,1], \
            linestyle='None', mfc=fc, marker='o');
    return ax;

  def plot_edges(self, ax=None, fc='blue'):
    " plot edges using matplotlib "
    if ax is None: plt.figure(); ax=plt.subplot(111);
    lc = c.LineCollection([self.points[e] for e in self.edges]);
    lc.set_color(fc);
    ax.add_collection(lc);
    return ax;

  def plot_tiles(self, ax=None, nvertices=None, fc='blue', alpha=0.5):
    " plot tiles "
    if ax is None: plt.figure(); ax=plt.subplot(111);
    # sort tiles according to their number of vertices
    N=max([len(v) for v in self.vertices]);
    if nvertices is None:
      nvertices=range(N);

    tileN=[ [[None,None]] for i in range(N+1) ];
    for v in self.vertices:
      if len(v)>0:
        tileN[len(v)].extend(self.points[v].tolist()+[[None,None]]);

    # plot tiles
    for n in nvertices:
      if n>N: continue;
      x,y = zip(*(tileN[n]));
      ax.fill(x,y, facecolor=fc, alpha=alpha, edgecolor='none');

    return ax;

  def __get_polygon(self,v):
    " return polygon that include Delaunay vertex v (sorted clockwise)"

    # search triangles that contain vertex v (t... triangle, n... which corner)
    t,n = np.where(tri.vertices == v);  
    # calculate vector from Delaunay vertex v to center of triangle t
    delta=self.points[t] - self.tri.points[v];
    # sort triagles using angle of vector to x-axis
    return t[ np.argsort(np.arctan2(*tuple(delta.T))) ];
  


# --- self-test -------------------------------------------------------------
if __name__ == '__main__':

  # Delaunay triangulation
  points = np.genfromtxt("tests/graphene_flower.txt");
  Delaunay = Tiling(points);
  ax=Delaunay.plot_vertices(fc='red');
  #Delaunay.plot_tiles(ax,[3],'red');
  Delaunay.plot_edges(ax,fc='red');


  # Voronoi diagram
  Voronoi=Delaunay.get_dual();
  ax2=Voronoi.plot_vertices(ax,fc='blue');
  Voronoi.plot_edges(ax);
  Voronoi.plot_tiles(ax,[7],'blue');

  D = Voronoi.get_dual();
  #V = D.get_dual();
  #D = V.get_dual();
  D.plot_vertices(ax,'green');
  D.plot_edges(ax,'green');

  D.flip(100);

  for x in (Delaunay, Voronoi, D):
    print x.npoints, x.ntiles, x.nedges, len(x.neighbors)
  plt.show();

