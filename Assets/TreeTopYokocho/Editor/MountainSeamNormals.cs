#if UNITY_EDITOR && !COMPILER_UDONSHARP
// Editor-only, separately gated exact-twelve mountain seam normal refinement.
// Native source XYZ -> Unity (X,Z,Y), with triangle winding reversed on import.
// Does not weld vertices, change geometry/UV/colors, or touch unrelated meshes.
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

namespace TreeTopYokocho.Editor
{
    internal static class MountainSeamNormals
    {
        internal const double CreaseCosine = 0.5735764363510462; // cos(55 degrees).
        internal static readonly string[] Keys = new string[] {
            "Landscape/SnowRange_0__AlpineRock", "Landscape/SnowRange_0__AlpineSnow", "Landscape/SnowRange_0__AlpineSnowShade",
            "Landscape/SnowRange_1__AlpineRock", "Landscape/SnowRange_1__AlpineSnow", "Landscape/SnowRange_1__AlpineSnowShade",
            "Landscape/SnowRange_2__AlpineRock", "Landscape/SnowRange_2__AlpineSnow", "Landscape/SnowRange_2__AlpineSnowShade",
            "Landscape/SnowRange_3__AlpineRock", "Landscape/SnowRange_3__AlpineSnow", "Landscape/SnowRange_3__AlpineSnowShade"
        };
        // Exact native float32 XYZ bytes followed by original uint32 indices.
        static readonly string[] GeometrySha256 = new string[] { "47d0903ab8d35732b20c7a6eed622aba29d927a192d7a3bd78542fc9dbf4cdb6",
            "de3c66d50d4a60ae5a9f9e0ef14eaf36f81ff52b89cb5e93b82292b4481c310a",
            "e6e82466a007e077e6499ce6c45d57b61a09a3bafce4efefada1e11e0dfe03f8",
            "aec4f33f940ed6e8e46b75ba1c385965560b93315ab5b4a849ec7a821fec7497",
            "9eb391b50135b76654be3376b897dab7f53bac793346d2a96c62589a10c93a94",
            "5591fdb7d1e159e9134e75d71f291db9f78380936bdd67d5954851da0769aede",
            "6980cb9eac058a284e6a6abf4a374ff51653dac0c993747db5d286e7074bce4d",
            "b8acb38b33bd10db187d120be80c1fbd9aa4bff72e6e213d2d63262bf592f0c8",
            "ddebb882eb3520e7194c8c4eed2de0a9e79b84812f7937d3b33a07e067821435",
            "507cd82b8291d67f5451be44254d725934b5fffb1d682d6f62e61c9d90ff102d",
            "b70afe7309fc9468c48784aec79e4a666e69bf875f55ebcc1315247a6ac7fc96",
            "d4541f6caebaf9757e1e4a060231e63e0e5ed3a3a0af29832e9c7098629d439f" };
        internal static bool IsApproved(string group, string material) { return Array.IndexOf(Keys, group + "__" + material) >= 0; }

        struct Position : IEquatable<Position>, IComparable<Position>
        {
            internal float X, Y, Z;
            internal Position(float x, float y, float z) { X = x; Y = y; Z = z; }
            internal D3 Double() { return new D3(X, Y, Z); }
            public bool Equals(Position p) { return X.Equals(p.X) && Y.Equals(p.Y) && Z.Equals(p.Z); }
            public override bool Equals(object o) { return o is Position && Equals((Position)o); }
            public override int GetHashCode() { unchecked { return (X.GetHashCode() * 397 ^ Y.GetHashCode()) * 397 ^ Z.GetHashCode(); } }
            public int CompareTo(Position p) { int c = X.CompareTo(p.X); if (c != 0) return c; c = Y.CompareTo(p.Y); return c != 0 ? c : Z.CompareTo(p.Z); }
        }
        struct D3
        {
            internal double X, Y, Z;
            internal D3(double x, double y, double z) { X = x; Y = y; Z = z; }
            public static D3 operator +(D3 a, D3 b) { return new D3(a.X+b.X, a.Y+b.Y, a.Z+b.Z); }
            public static D3 operator -(D3 a, D3 b) { return new D3(a.X-b.X, a.Y-b.Y, a.Z-b.Z); }
            public static D3 operator *(D3 a, double b) { return new D3(a.X*b, a.Y*b, a.Z*b); }
            public static D3 operator /(D3 a, double b) { return new D3(a.X/b, a.Y/b, a.Z/b); }
            internal static double Dot(D3 a, D3 b) { return a.X*b.X + a.Y*b.Y + a.Z*b.Z; }
            internal static D3 Cross(D3 a, D3 b) { return new D3(a.Y*b.Z-a.Z*b.Y, a.Z*b.X-a.X*b.Z, a.X*b.Y-a.Y*b.X); }
            internal double Length() { return Math.Sqrt(X*X + Y*Y + Z*Z); }
        }
        struct Edge : IEquatable<Edge>
        {
            internal int A, B;
            internal Edge(int a, int b) { A = Math.Min(a,b); B = Math.Max(a,b); }
            public bool Equals(Edge e) { return A == e.A && B == e.B; }
            public override bool Equals(object o) { return o is Edge && Equals((Edge)o); }
            public override int GetHashCode() { unchecked { return A*397 ^ B; } }
        }
        sealed class Triangle : IComparable<Triangle>
        {
            internal int[] Ids;
            internal Position[] P;
            internal Triangle(int a, int b, int c, List<Position> positions)
            {
                int[] ids = new int[] {a,b,c}; int start = 0;
                for (int i=1;i<3;i++) if (positions[ids[i]].CompareTo(positions[ids[start]])<0) start=i;
                Ids=new int[] {ids[start],ids[(start+1)%3],ids[(start+2)%3]};
                P=new Position[] {positions[Ids[0]],positions[Ids[1]],positions[Ids[2]]};
            }
            public int CompareTo(Triangle other) { for (int i=0;i<3;i++) { int c=P[i].CompareTo(other.P[i]); if(c!=0)return c; } return 0; }
        }
        sealed class Input
        {
            internal Mesh Mesh;
            internal int[] GlobalIds;
            internal Vector3[] Normals;
        }
        static bool Finite(double x) { return !double.IsNaN(x) && !double.IsInfinity(x); }
        static string Hash(Vector3[] vertices, int[] unityTriangles)
        {
            using (var stream = new MemoryStream()) {
                using (var writer = new BinaryWriter(stream, System.Text.Encoding.UTF8, true)) {
                    foreach (var p in vertices) { writer.Write(p.x); writer.Write(p.z); writer.Write(p.y); }
                    for (int i=0;i<unityTriangles.Length;i+=3) { writer.Write(unityTriangles[i]); writer.Write(unityTriangles[i+2]); writer.Write(unityTriangles[i+1]); }
                }
                using (var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream.ToArray())).Replace("-", "").ToLowerInvariant();
            }
        }

        internal static void Apply(Dictionary<string, Mesh> mountainMeshes)
        {
            if (mountainMeshes.Count != 12) throw new InvalidDataException("Expected exact twelve mountain meshes for seam normals.");
            var positions=new List<Position>(); var lookup=new Dictionary<Position,int>();
            var owners=new List<HashSet<int>>(); var triangles=new List<Triangle>(); var inputs=new List<Input>();
            for (int owner=0;owner<Keys.Length;owner++) {
                Mesh mesh;
                if (!mountainMeshes.TryGetValue(Keys[owner],out mesh)) throw new InvalidDataException("Missing approved mountain mesh: "+Keys[owner]);
                Vector3[] v=mesh.vertices; int[] f=mesh.triangles; Vector3[] normals=mesh.normals;
                if(f.Length<3 || f.Length%3!=0 || normals.Length!=v.Length) throw new InvalidDataException("Invalid mountain normal input.");
                if(Hash(v,f)!=GeometrySha256[owner]) throw new InvalidDataException("Unapproved mountain geometry for normal pass: "+Keys[owner]);
                var ids=new int[v.Length];
                for(int i=0;i<v.Length;i++) {
                    if(!Finite(v[i].x)||!Finite(v[i].y)||!Finite(v[i].z)) throw new InvalidDataException("Non-finite normal source.");
                    var p=new Position(v[i].x,v[i].z,v[i].y); int id;
                    if(!lookup.TryGetValue(p,out id)) { id=positions.Count; lookup.Add(p,id); positions.Add(p); owners.Add(new HashSet<int>()); }
                    ids[i]=id; owners[id].Add(owner);
                }
                // Restore the native/source winding before source-coordinate math.
                for(int i=0;i<f.Length;i+=3) {
                    int a=f[i],b=f[i+2],c=f[i+1];
                    if(a<0||b<0||c<0||a>=v.Length||b>=v.Length||c>=v.Length) throw new InvalidDataException("Invalid normal-source index.");
                    triangles.Add(new Triangle(ids[a],ids[b],ids[c],positions));
                }
                inputs.Add(new Input {Mesh=mesh,GlobalIds=ids,Normals=normals});
            }
            triangles.Sort(); // Canonical coordinate order, independent of import order.
            var sums=new D3[positions.Count]; var faceNormals=new List<D3>(); var edges=new Dictionary<Edge,List<int>>();
            for(int face=0;face<triangles.Count;face++) {
                Triangle t=triangles[face]; D3[] p=new D3[] {t.P[0].Double(),t.P[1].Double(),t.P[2].Double()};
                D3 cross=D3.Cross(p[1]-p[0],p[2]-p[0]); double length=cross.Length();
                if(!Finite(length)||length<=1e-12) throw new InvalidDataException("Degenerate triangle in normal source.");
                D3 n=cross/length; faceNormals.Add(n);
                for(int j=0;j<3;j++) {
                    D3 a=p[(j+1)%3]-p[j],b=p[(j+2)%3]-p[j]; double angle=Math.Atan2(D3.Cross(a,b).Length(),D3.Dot(a,b));
                    if(!Finite(angle)||angle<=0) throw new InvalidDataException("Invalid normal corner angle.");
                    sums[t.Ids[j]]=sums[t.Ids[j]]+n*angle;
                    var edge=new Edge(t.Ids[j],t.Ids[(j+1)%3]); List<int> faces;
                    if(!edges.TryGetValue(edge,out faces)) { faces=new List<int>(); edges.Add(edge,faces); } faces.Add(face);
                }
            }
            var crease=new HashSet<int>(); int sharpEdges=0;
            foreach(var edge in edges) {
                var faces=edge.Value;
                if(faces.Count>2) throw new InvalidDataException("Non-manifold mountain normal input.");
                if(faces.Count==2 && D3.Dot(faceNormals[faces[0]],faceNormals[faces[1]])<CreaseCosine) { crease.Add(edge.Key.A); crease.Add(edge.Key.B); sharpEdges++; }
            }
            var shared=new Dictionary<int,Vector3>(); int excluded=0;
            for(int i=0;i<positions.Count;i++) {
                if(owners[i].Count<2) continue;
                if(crease.Contains(i)) { excluded++; continue; }
                double length=sums[i].Length();
                if(!Finite(length)||length<=1e-12) throw new InvalidDataException("Zero or invalid shared mountain normal.");
                D3 n=sums[i]/length;
                // Reflection matches imported native positions and reversed winding.
                shared.Add(i,new Vector3((float)n.X,(float)n.Z,(float)n.Y));
            }
            // No mesh mutation until all inputs and computed normals are valid.
            int slots=0;
            foreach(Input input in inputs) {
                for(int i=0;i<input.GlobalIds.Length;i++) { Vector3 normal; if(shared.TryGetValue(input.GlobalIds[i],out normal)) { input.Normals[i]=normal; slots++; } }
            }
            foreach(Input input in inputs) { input.Mesh.normals=input.Normals; input.Mesh.RecalculateTangents(); EditorUtility.SetDirty(input.Mesh); }
            Debug.Log("Mountain seam normals: "+shared.Count+" shared positions, "+slots+" normal slots, "+excluded+" sharp seam positions preserved, "+sharpEdges+" actual crease edges. Geometry unchanged.");
        }
    }
}

#endif
