from time import sleep, perf_counter
from math import cos, sin, radians, ceil, floor
from json import loads
import copy
from threading import Thread
from socket import socket, AF_INET
import re


class Server(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.command = ''

        
    def run(self):
        sock = socket(AF_INET)
        sock.bind(('',2805))
        print ('ready to listen')
        sock.listen(1)
        print ('got connection')
        conn,addr = sock.accept()
        print('accepted')
        while True:
            data = conn.recv(128)
            if not data:
                break
            self.command = data.decode('ascii','ignore').casefold()


class Matrix4:
    def __init__(self):
        self.matrix = [0] * 16

    def __repr__(self):
        result = ''
        for i in range(16):
            result += '{:^7.3f}'.format(self.matrix[i])
            if (i + 1) % 4 == 0:
                result += '\n'
        return result


class RotMatrix(Matrix4):
    def __init__(self, angle, axis):
        Matrix4.__init__(self)
        self.angle = radians(angle)
        if axis == 'x':
            self.matrix = [1, 0, 0, 0,
                           0, cos(self.angle), -sin(self.angle), 0,
                           0, sin(self.angle), cos(self.angle), 0,
                           0, 0, 0, 1]
        elif axis == 'y':
            self.matrix = [cos(self.angle), 0, sin(self.angle), 0,
                           0, 1, 0, 0,
                           -sin(self.angle), 0, cos(self.angle), 0,
                           0, 0, 0, 1]
        elif axis == 'z':
            self.matrix = [cos(self.angle), -sin(self.angle), 0, 0,
                           sin(self.angle), cos(self.angle), 0, 0,
                           0, 0, 1, 0,
                           0, 0, 0, 1]


class SkewMatrix(Matrix4):
    def __init__(self, kxy, kxz, kyx, kyz, kzx, kzy):
        Matrix4.__init__(self)
        self.matrix = [1, kyx, kzx, 0,
                       kxy, 1, kzy, 0,
                       kxz, kyz, 1, 0,
                       0, 0, 0, 1]


class ShiftMatrix(Matrix4):
    def __init__(self, kx, ky, kz):
        Matrix4.__init__(self)
        self.matrix = [1, 0, 0, kx,
                       0, 1, 0, ky,
                       0, 0, 1, kz,
                       0, 0, 0, 1]


class OppMatrix(Matrix4):
    def __init__(self, kx, ky, kz):
        Matrix4.__init__(self)
        self.matrix = [1, 0, 0, 0,
                       0, 1, 0, 0,
                       0, 0, 1, 0,
                       kx, ky, kz, 1]


class ScaleMatrix(Matrix4):
    def __init__(self, kx, ky, kz):
        Matrix4.__init__(self)
        self.matrix = [kx, 0, 0, 0,
                       0, ky, 0, 0,
                       0, 0, kz, 0,
                       0, 0, 0, 1]


class Point:
    def __init__(self, x, y, z, h=1):
        self.x = x
        self.y = y
        self.z = z
        self.h = h

    def __repr__(self):
        return 'Point at x:{}, y:{}, z:{}'.format(self.x, self.y, self.z)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y, self.z + other.z)

    def copy(self, other):
        self.x = other.x
        self.y = other.y
        self.z = other.z
        self.h = other.h

    def apply_matrix(self, matrix):
        
        x = self.x * matrix.matrix[0] + \
            self.y * matrix.matrix[1] + \
            self.z * matrix.matrix[2] + \
            self.h * matrix.matrix[3]
        y = self.x * matrix.matrix[4] + \
            self.y * matrix.matrix[5] + \
            self.z * matrix.matrix[6] + \
            self.h * matrix.matrix[7]
        z = self.x * matrix.matrix[8] + \
            self.y * matrix.matrix[9] + \
            self.z * matrix.matrix[10] + \
            self.h * matrix.matrix[11]
        h = self.x * matrix.matrix[12] + \
            self.y * matrix.matrix[13] + \
            self.z * matrix.matrix[14] + \
            self.h * matrix.matrix[15]
        if -0.01 > h < 0:
            h = -0.01
        elif 0 <= h < 0.01:
            h = 0.01
        
        self.x = x / h
        self.y = y / h
        self.z = z / h
        self.h = 1
        

class Line:
    def __init__(self, point1, point2):
        self.point1 = point1
        self.point2 = point2
        self.x1 = point1.x
        self.x2 = point2.x
        self.y1 = point1.y
        self.y2 = point2.y


class Face:
    def __init__(self, color, point1: Point, point2: Point, point3: Point):
        self.a = point1
        self.b = point2
        self.c = point3
        self.color = color

    def boundaries(self):
        self.left = ceil(max(min((self.a.x)*2, (self.b.x)*2, (self.c.x-1)*2), -37))
        self.right = ceil(min(max((self.a.x) * 2, (self.b.x) * 2, (self.c.x) * 2), 38))
        self.lower = ceil(max(min(self.a.y-1, self.b.y-1, self.c.y-1), -10))
        self.upper = ceil(min(max(self.a.y+1, self.b.y+1, self.c.y+1), 11))


    def intersection(self, point: Point):
        # TRIANGLE x POINT INTESRSECTION CHECK #
        d1 = (self.a.x - point.x)*(self.b.y - self.a.y)-(self.b.x-self.a.x)*(self.a.y-point.y)
        d2 = (self.b.x - point.x)*(self.c.y - self.b.y)-(self.c.x-self.b.x)*(self.b.y-point.y)
        d3 = (self.c.x - point.x)*(self.a.y - self.c.y)-(self.a.x-self.c.x)*(self.c.y-point.y)
        if (d1 <= 0 and d2 <= 0 and d3 <= 0) or (d1 >= 0 and d2 >= 0 and d3 >= 0):
            pass
        else:
            o = Point(0,0,-100)+point
            return o
        # Z CALCULATION #
            # NORMAL CALCULATION #
        v1x = self.a.x - self.b.x
        v1y = self.a.y - self.b.y
        v1z = self.a.z - self.b.z

        v2x = self.b.x - self.c.x
        v2y = self.b.y - self.c.y
        v2z = self.b.z - self.c.z
        length = ((v1y * v2z - v1z * v2y)**2 + (v1z * v2x - v1x * v2z)**2 + (v1x * v2y - v1y * v2x)**2)**0.5
        if length == 0:
            length = 0.01
        nx = (v1y * v2z - v1z * v2y) / length
        ny = (v1z * v2x - v1x * v2z) / length
        nz = (v1x * v2y - v1y * v2x) / length
        n = Point(nx, ny, nz)
            # DISTANCE #
        v = self.a-point
        d = (n.x*v.x+n.y*v.y+n.z*v.z)
        w = Point(0,0,1)
        e = (n.z)
        if not e == 0:
            o = Point(0, 0, d/e)+point
        else:
            o = Point(0, 0, -100)+point
        return o


class Screen:
    def __init__(self, fill=' '):
        self.screen = [fill, ] * 80 * 24
        self.zbuffer = [-100] * 80 * 24
        for y in range(1, 25):
            self.screen[(y * 80) - 1] = '\n'
            self.screen[(y * 80) - 2] = '║'
            self.screen[(y * 80) - 80] = '║'
            if y == 1 or y == 24:
                for x in range(1, 80):
                    self.screen[((y - 1) * 80) + x - 1] = '═'
        self.screen[0] = '╔'
        self.screen[78] = '╗'
        self.screen[24 * 80 - 80] = '╚'
        self.screen[24 * 80 - 2] = '╝'
        self.screen[24 * 80 - 1] = '\n'
        self.fps = '  '
        self.perftimer = perf_counter()


    def __repr__(self):
        self.fps = str((1.0 / (perf_counter() - self.perftimer)))
        self.perftimer = perf_counter()
        self.screen[83] = self.fps[0]
        self.screen[84] = self.fps[1]
        r = ''.join(self.screen)
        return r

    def clear(self, fill=' '):
        for y in range(1,23):
            for x in range(2,79):
                self.screen[x + y * 80 - 1] = fill
                self.zbuffer[x + y * 80 - 1] = -100

    # DRAW POINT #
    def draw_point_xy(self, x, y):
        if x < -19 or x > 19 or y > 10 or y < -11:
            pass
        else:
            self.screen[round(x * 2) + 40 + (round(-y) + 11) * 80 - 1] = '*'


    def draw_point_p(self, point: Point):
        self.draw_point_xy(point.x, point.y)

    # DRAW LINE #
    def draw_line_l(self, line: Line):
        self.draw_line_pp(line.point1, line.point2)

    def draw_line_pp(self, point1: Point, point2: Point):
        self.draw_line_xy(point1.x, point1.y, point2.x, point2.y)

    def draw_line_xy(self, x1, y1, x2, y2, first=True):
        if first:
            self.draw_point_xy(x1, y1)
            self.draw_point_xy(x2, y2)
        midpointX = ((x1 + x2) / 2)
        midpointY = ((y1 + y2) / 2)
        if (abs(midpointX - x1) < 0.25 and abs(midpointY - y1) < 0.5) or (
                abs(midpointX - x2) < 0.25 and abs(midpointY - y2) < 0.5):
            return
        else:
            self.draw_point_xy(midpointX, midpointY)
            self.draw_line_xy(midpointX, midpointY, x2, y2, first=False)
            self.draw_line_xy(x1, y1, midpointX, midpointY, first=False)

    # DRAW FACE #
    def render(self, face: Face):
        face.boundaries()
        for y in range(face.lower-1, face.upper):
            for x in range(face.left-1, face.right+1):
                ray = Point(x / 2, y, 0)
                z = face.intersection(ray).z
                if self.zbuffer[round(x) + 40 + (round(-y) + 11) * 80 - 1] < z:
                    self.zbuffer[round(x) + 40 + (round(-y) + 11) * 80 - 1] = z
                    if z > -100:
                        self.screen[round(x) + 40 + (round(-y) + 11) * 80 - 1] = face.color

def load_file(filename ,pointslist, lineslist, faceslist, showpoints):
    pointslist = []
    lineslist = []
    faceslist = []
    with open(filename, 'r') as file:
        model = file.read()
        #print(model)
        js = loads(model)
        #print(js)
        for point in js['Points']:
            newpoint = Point(point['X'], point['Y'], point['Z'])
            pointslist.append(newpoint)

        #print(pointslist)
        showpoints = copy.deepcopy(pointslist)
        for line in js['Lines']:
            #print(line)
            newline = Line(showpoints[line['Point1']], showpoints[line['Point2']])
            #print(newline)
            lineslist.append(newline)
        for face in js['Faces']:
            #print(face)
            newface = Face(face['Color'],
                           showpoints[face['Point1']],
                           showpoints[face['Point2']],
                           showpoints[face['Point3']])
            #print(newface)
            faceslist.append(newface)
    return pointslist, lineslist, faceslist, showpoints


# MAIN #
server = Server()
server.daemon = True
server.start()
pointslist = []
lineslist = []
faceslist = []
showpoints = []
mainscreen = Screen(fill=' ')
n = OppMatrix(0, 0, -0.03)
k = SkewMatrix(0, 0, 0.0, 0.0, -0.4, -0.4)
m = RotMatrix(0,'y')

while True:
    mainscreen.clear()
    if server.command:
        # LOAD #
        match = re.match('(load)\s+(\w+)', server.command)
        if match:
            pointslist, lineslist, faceslist, showpoints = load_file(match[2]+'.json', pointslist, lineslist, faceslist, showpoints)
            server.command = ''
        # ROT #
        match = re.match('(rot)\s+(-?\d+)\s+([xyz])', server.command)
        if match:
            m = RotMatrix(int(match[2]), match[3])
            for point in pointslist:
                point.apply_matrix(m)
            m = RotMatrix(0, 'y')
            server.command = ''
        # SPIN #
        match = re.match('(spin)\s+([xyz])', server.command)
        if match:
            m = RotMatrix(1, match[2])
            server.command = ''
        # STOP #
        match = re.match('(stop)', server.command)
        if match:
            m = RotMatrix(0, 'y')
            server.command = ''
        # SHIFT #
        match = re.match('(shift)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)', server.command)
        if match:
            m = ShiftMatrix(int(match[2]),int(match[3]),int(match[4]))
            for point in pointslist:
                point.apply_matrix(m)
            m = RotMatrix(0, 'y')
            server.command = ''
        # SCALE #
        match = re.match('(scale)\s+(-?\d?[\.\,]?\d+)\s+(-?\d?[\.\,]?\d+)\s+(-?\d?[\.\,]?\d+)', server.command)
        if match:
            m = ScaleMatrix(float(match[2]),float(match[3]),float(match[4]))
            for point in pointslist:
                point.apply_matrix(m)
            m = RotMatrix(0, 'y')
            server.command = ''
        # SKEW #
        match = re.match('(skew)\s+([10])', server.command)
        if match:
            if match[2] == '1':
                k = SkewMatrix(0, 0, 0.0, 0.0, -0.4, -0.4)
            if match[2] == '0':
                k = SkewMatrix(0, 0, 0, 0, 0, 0)
            server.command = ''
        # PROJ #
        match = re.match('(proj)\s+([10])', server.command)
        if match:
            if match[2] == '1':
                n = OppMatrix(0, 0, -0.03)
            if match[2] == '0':
                n = OppMatrix(0, 0, 0)
            server.command = ''

    for point in pointslist:
        point.apply_matrix(m)

    for i, point in enumerate(showpoints):
        point.copy(pointslist[i])
        point.apply_matrix(k)
        point.apply_matrix(n)
    #for line in lineslist:
        #mainscreen.draw_line_l(line)
    for face in faceslist:
        mainscreen.render(face)

    print(mainscreen, end='')
    sleep(0)
    

