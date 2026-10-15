import unittest
from automation.geometry.assembly_envelopes import compare,screen


def box(name,centre,size):return dict(name=name,centre_mm=centre,size_mm=size)


class AssemblyEnvelopeTests(unittest.TestCase):
    def test_diagonal_gap_and_face_contact(self):
        a=box('a',[0,0,0],[2,2,2]);b=box('b',[5,6,0],[2,2,2])
        self.assertEqual(compare(a,b)['minimum_distance_mm'],5)
        b['centre_mm']=[2,0,0]
        self.assertEqual(compare(a,b)['interference_volume_mm3'],0)

    def test_contact_intent_does_not_hide_other_interference(self):
        a=box('a',[0,0,0],[2,2,2]);b=box('b',[1,0,0],[2,2,2]);c=box('c',[1,1,0],[2,2,2])
        r=screen([a,b,c],{frozenset(('a','b')):'Compressed gasket envelope'})
        self.assertEqual(len(r['intersections']),3)
        self.assertEqual(len(r['unexplained_intersections']),2)
        self.assertEqual(compare(a,b)['interference_volume_mm3'],4)


if __name__=='__main__':unittest.main()
