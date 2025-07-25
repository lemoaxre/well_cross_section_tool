class Segment: 
    def __init__(self, seg_id, wells_list):
        self.seg = seg_id
        self.wells = wells_list
        self.starting_well = None
    
    def getSegId(self):
        return self.seg
    
    def getWells(self):
        return self.wells
        
    def setFirstWell(self, well):
        for i in self.wells:
            if i == well:
                self.starting_well = well
    
    def getFirstWell(self):
        return self.starting_well