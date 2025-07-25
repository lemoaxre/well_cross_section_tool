class SegEquation:
    def __init__(self, dist, coeff):
        self.dist = dist 
        self.coeff = coeff 
    
    def getDist(self):
        return self.dist 
    
    def getCoeff(self):
        return self.coeff 
    
    def onSeg(self, pos):
        if pos < self.getDist():
            return True 
        else:
            return False 
    
    def getYPos(self, x):
        coeff = self.getCoeff() 
        y = coeff[0] * (x ** 2) + coeff[1] * x + coeff[2]
        return y
        
